"""vps_runner — Ansible-native VPS lifecycle plugin core.

- Uses ansible_runner.run() instead of subprocess + ansible-playbook
- Reads from standard inventory (inventory/vps_runner/<env>/) — no custom state
- per-host structured results via Runner.host_events() / Runner.stats
- Explicit envvars whitelist + suppress_env_files=True + rotate_artifacts=10
  + forks=20 (W-R18 hardening). suppress_env_files avoids the env/ file
  but does NOT scrub the `command` artifact, so we must not pass any
  variable that could carry secrets through `envvars`.

This module is the library layer; cli.py provides the user-facing entry.
Full spec: docs/reference/feature-map/vps-runner.md.
"""

from __future__ import annotations

import contextlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

try:
    import ansible_runner
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "ansible-runner is required. Run: pip install -e . "
        "(or pip install -r requirements.txt)"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_ROOT = PROJECT_ROOT / "inventory" / "vps_runner"
ARTIFACT_ROOT = PROJECT_ROOT / "runtime" / "logs" / "vps_runner"
ANSIBLE_LOCAL_TEMP = PROJECT_ROOT / ".ansible" / "tmp"
PLAYBOOK_DIR = Path(__file__).resolve().parent / "playbooks"
SSH_CONFIG_TEMPLATE = PLAYBOOK_DIR / "templates" / "ssh_config_entry.j2"
DEFAULT_SSH_CONFIG_DIR = Path("~/.ssh/config.d").expanduser()
DEFAULT_SSH_MAIN_CONFIG = Path("~/.ssh/config").expanduser()
DEFAULT_PERSONAL_IDENTITY_FILE = Path("~/.ssh/id_ed25519").expanduser()

DEFAULT_FORKS = 20
DEFAULT_ROTATE_ARTIFACTS = 10
SUPPORTED_ENVS = ("dev", "stag", "prod")

# envvars whitelist: only these are forwarded to ansible-runner. Anything not
# strictly required to invoke ansible-playbook from the active venv is dropped
# so secrets in the caller's process env never reach `runtime/logs/.../command`.
_ENVVAR_WHITELIST = ("HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM")

# Input charset policies. Each is the *primary* defense; resolved-path
# containment checks (see _assert_path_in_dir) are belt-and-braces.
# - alias: filesystem path component + YAML key + j2 input. Conservative:
#   alnum + `_-.`, must start alnum (no leading dash → no flag-spoof; no
#   leading dot → no hidden-file shenanigans). Length ≤63 keeps Ansible
#   "limit" CLI string + inventory yaml readable.
# - hostname: SSH HostName value. Reject whitespace / newline / `#` so the
#   rendered config line can't break out into another directive.
# - ssh user: POSIX-ish username. Reject anything outside `[A-Za-z_][A-Za-z0-9_-]*`.
_VALID_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
_VALID_HOSTNAME_RE = re.compile(r"^[^\s#]+$")
_VALID_SSH_USER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_MAX_ALIAS_LEN = 63
_MAX_HOSTNAME_LEN = 253
_MAX_SSH_USER_LEN = 32


class VpsRunnerError(Exception):
    """Base plugin error."""


def _validate_alias(alias: Any) -> str:
    """Return alias unchanged iff it matches _VALID_ALIAS_RE and is ≤63 chars.

    Rejects: empty, non-str, traversal (`/`, `\\`, `..`), leading dash / dot,
    whitespace / newlines (SSH-config injection vector), control chars,
    over-long values. Raises VpsRunnerError with a single human-readable message.
    """
    if not isinstance(alias, str) or not alias:
        raise VpsRunnerError("alias must be a non-empty string")
    if len(alias) > _MAX_ALIAS_LEN:
        raise VpsRunnerError(
            f"alias too long ({len(alias)} > {_MAX_ALIAS_LEN} chars)"
        )
    if not _VALID_ALIAS_RE.match(alias):
        raise VpsRunnerError(
            f"alias {alias!r} invalid; allowed charset: letters/digits/_-., "
            f"must start with letter or digit, ≤{_MAX_ALIAS_LEN} chars"
        )
    return alias


def _validate_hostname(hostname: Any) -> str:
    """Return hostname unchanged iff free of whitespace/newlines/`#` and ≤253 chars.

    Accepts IPv4, IPv6 (colons OK), DNS names. Rejects values that could break
    out of the SSH HostName directive (newline → directive injection; `#` →
    SSH config comment; whitespace → SSH config field separator).
    """
    if not isinstance(hostname, str) or not hostname:
        raise VpsRunnerError("hostname must be a non-empty string")
    if len(hostname) > _MAX_HOSTNAME_LEN:
        raise VpsRunnerError(
            f"hostname too long ({len(hostname)} > {_MAX_HOSTNAME_LEN} chars)"
        )
    if not _VALID_HOSTNAME_RE.match(hostname):
        raise VpsRunnerError(
            f"hostname {hostname!r} invalid; reject any whitespace, newline, or '#'"
        )
    return hostname


def _validate_ssh_user(user: Any) -> str:
    """Return user unchanged iff matches `[A-Za-z_][A-Za-z0-9_-]*` and ≤32 chars."""
    if not isinstance(user, str) or not user:
        raise VpsRunnerError("ssh user must be a non-empty string")
    if len(user) > _MAX_SSH_USER_LEN:
        raise VpsRunnerError(
            f"ssh user too long ({len(user)} > {_MAX_SSH_USER_LEN} chars)"
        )
    if not _VALID_SSH_USER_RE.match(user):
        raise VpsRunnerError(
            f"ssh user {user!r} invalid; allowed charset: "
            f"[A-Za-z_][A-Za-z0-9_-]*, ≤{_MAX_SSH_USER_LEN} chars"
        )
    return user


def _assert_path_in_dir(path: Path, parent: Path) -> None:
    """Belt-and-braces: after building `path` from possibly-user-controlled
    alias, assert it resolves under `parent`. Catches any traversal the
    charset regex missed (symlink edge cases, OS-specific normalizations).
    """
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        raise VpsRunnerError(
            f"path traversal blocked: {path} not under {parent}"
        ) from None


@dataclass(frozen=True)
class HostResult:
    """Structured per-host outcome from a Runner invocation."""

    alias: str
    status: str  # ok | failed | unreachable | skipped
    message: str = ""
    events: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class RunSummary:
    """High-level summary of a single ansible-runner invocation."""

    run_id: str
    action: str
    env: str
    status: str  # successful | failed | timeout | canceled
    rc: int
    artifact_dir: str
    hosts: list[HostResult]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generate_run_id(action: str, env: str) -> str:
    return f"vps-runner-{utc_timestamp()}-{env}-{action}"


def inventory_path(env: str) -> Path:
    if env not in SUPPORTED_ENVS:
        raise VpsRunnerError(
            f"unsupported env: {env!r}; expected one of {SUPPORTED_ENVS}"
        )
    path = INVENTORY_ROOT / env
    if not path.exists():
        raise VpsRunnerError(
            f"inventory directory missing: {path} "
            f"(expected vps_runner inventory tree)"
        )
    return path


def list_aliases(env: str) -> list[str]:
    """Return sorted alias list from hosts.yml (no host_vars read)."""
    inv_dir = inventory_path(env)
    hosts_file = inv_dir / "hosts.yml"
    if not hosts_file.exists():
        return []
    with hosts_file.open("r", encoding="utf-8") as f:
        hosts_data = yaml.safe_load(f) or {}
    children = (hosts_data.get("all") or {}).get("children") or {}
    targets = children.get("vps_targets") or {}
    return sorted((targets.get("hosts") or {}).keys())


def host_vars_path(env: str, alias: str) -> Path:
    _validate_alias(alias)
    parent = inventory_path(env) / "host_vars"
    target = parent / f"{alias}.yml"
    _assert_path_in_dir(target, parent)
    return target


def read_host_vars(env: str, alias: str) -> dict[str, Any]:
    """Return parsed host_vars/<alias>.yml; raise if missing."""
    path = host_vars_path(env, alias)
    if not path.exists():
        raise VpsRunnerError(f"host_vars not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_host_vars(env: str, alias: str, data: dict[str, Any]) -> None:
    """Write data to host_vars/<alias>.yml (sorted keys disabled to preserve schema)."""
    path = host_vars_path(env, alias)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def record_run(
    env: str, alias: str, summary: "RunSummary", *, set_status: str | None = None
) -> None:
    """Update host_vars vps_runner.last_run + updated_at after a run."""
    data = read_host_vars(env, alias)
    vr = data.setdefault("vps_runner", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    vr["last_run"] = {
        "id": summary.run_id,
        "action": summary.action,
        "status": summary.status,
        "rc": summary.rc,
        "completed_at": now,
    }
    vr["updated_at"] = now
    if set_status is not None:
        vr["status"] = set_status
    write_host_vars(env, alias, data)


def remove_alias_from_hosts(env: str, alias: str) -> bool:
    """Drop alias from hosts.yml vps_targets.hosts. Returns True if changed."""
    inv_dir = inventory_path(env)
    hosts_file = inv_dir / "hosts.yml"
    if not hosts_file.exists():
        return False
    with hosts_file.open("r", encoding="utf-8") as f:
        hosts_data = yaml.safe_load(f) or {}
    children = (hosts_data.get("all") or {}).get("children") or {}
    targets = children.get("vps_targets") or {}
    host_map = targets.get("hosts") or {}
    if alias not in host_map:
        return False
    del host_map[alias]
    targets["hosts"] = host_map
    with hosts_file.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(
            hosts_data, f, default_flow_style=False, sort_keys=False
        )
    return True


def add_alias_to_hosts(env: str, alias: str) -> bool:
    """Add alias to hosts.yml vps_targets.hosts. Returns True if changed.

    Raises VpsRunnerError if alias already present (caller decides whether
    that's an error vs. no-op). Creates the all/children/vps_targets/hosts
    tree if missing (fresh-env case).
    """
    inv_dir = inventory_path(env)
    hosts_file = inv_dir / "hosts.yml"
    if hosts_file.exists():
        with hosts_file.open("r", encoding="utf-8") as f:
            hosts_data = yaml.safe_load(f) or {}
    else:
        hosts_data = {}
    all_block = hosts_data.setdefault("all", {})
    children = all_block.setdefault("children", {})
    targets = children.setdefault("vps_targets", {})
    host_map = targets.setdefault("hosts", {}) or {}
    if alias in host_map:
        raise VpsRunnerError(
            f"alias '{alias}' already in {hosts_file}"
        )
    host_map[alias] = None
    targets["hosts"] = host_map
    with hosts_file.open("w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(
            hosts_data, f, default_flow_style=False, sort_keys=False
        )
    return True


def add_host(
    env: str,
    alias: str,
    *,
    ip: str,
    port: int = 1156,
    user: str = "ansible",
    status: str = "pending",
) -> Path:
    """Create a new managed-VPS inventory entry.

    Writes host_vars/<alias>.yml (slim per-host overrides only; shared defaults
    come from group_vars/vps_targets.yml at play time) AND adds the alias to
    hosts.yml under vps_targets.hosts.

    Validates: alias must not already exist in either hosts.yml or
    host_vars/<alias>.yml; port must be in [1024, 65535] and != 22 (mirrors
    onboard.yml `pre_tasks` assertion to fail at CLI time, not mid-onboard).

    Returns the path to the created host_vars file.
    """
    _validate_alias(alias)
    ip = _validate_hostname(ip.strip() if isinstance(ip, str) else ip)
    user = _validate_ssh_user(user.strip() if isinstance(user, str) else user)
    if port == 22:
        raise VpsRunnerError(
            f"port=22 not allowed for managed_port (use a non-22 high port)"
        )
    if not (1024 <= port <= 65535):
        raise VpsRunnerError(
            f"port={port} out of range; must be 1024..65535"
        )

    hv_path = host_vars_path(env, alias)
    if hv_path.exists():
        raise VpsRunnerError(f"host_vars already exists: {hv_path}")
    if alias in list_aliases(env):
        raise VpsRunnerError(
            f"alias '{alias}' already in hosts.yml (orphaned entry; "
            f"clean it first or pick a different alias)"
        )

    data: dict[str, Any] = {
        "ansible_host": ip,
        "ansible_port": int(port),
        "ansible_user": user,
        "vps_runner": {
            "managed_port": int(port),
            "managed_user": user,
            "status": status,
            "os": {
                "family": None,
                "distribution": None,
                "version": None,
            },
        },
    }
    write_host_vars(env, alias, data)
    add_alias_to_hosts(env, alias)
    return hv_path


def delete_host_vars(env: str, alias: str) -> bool:
    """Delete host_vars/<alias>.yml. Returns True if removed."""
    path = host_vars_path(env, alias)  # validates alias + containment
    if not path.exists():
        return False
    path.unlink()
    return True


def list_hosts(env: str) -> list[dict[str, Any]]:
    """Return list of host metadata for the given env (no Ansible call).

    Reads hosts.yml + host_vars/<alias>.yml directly. Cheap, sync, used
    by `vps-runner list`.
    """
    inventory_path(env)  # surface missing-env / unsupported-env early
    aliases = list_aliases(env)

    results: list[dict[str, Any]] = []
    for alias in aliases:
        # Route through host_vars_path() chokepoint so a malformed alias in
        # hosts.yml (hand-edit corruption) fails loud instead of silently
        # reading a file outside host_vars/. Same charset + containment policy
        # as add_host (see R9 charset rationale).
        host_file = host_vars_path(env, alias)
        if host_file.exists():
            with host_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        results.append(
            {
                "alias": alias,
                "host": data.get("ansible_host", ""),
                "port": data.get("ansible_port", ""),
                "user": data.get("ansible_user", ""),
                "status": (data.get("vps_runner") or {}).get("status", "unknown"),
                "last_action": (
                    (data.get("vps_runner") or {}).get("last_run") or {}
                ).get("action", ""),
                "updated_at": (data.get("vps_runner") or {}).get(
                    "updated_at", ""
                ),
            }
        )
    return results


def _build_runner_envvars() -> dict[str, str]:
    """Build the minimal envvars passed to ansible-runner.

    Goals:
    - Always include the active venv's bin dir in PATH so `python -m
      plugins.vps_runner.cli` works without relying on the operator's PATH
      (Makefile-independent — see codex review P1.4).
    - Carry ANSIBLE_CONFIG + the project's collections/roles paths so
      ansible-playbook resolves to the correct config and content.
    - Pin ANSIBLE_LOCAL_TEMP to a project-local dir so the plugin works
      when ~/.ansible/tmp is missing/read-only (mirrors Makefile so the
      plugin is invariant to the operator's HOME state).
    - Forward only a small allowlist of innocuous locale/HOME vars (see
      _ENVVAR_WHITELIST); do NOT pass arbitrary caller env (P1.3).

    Note: sys.prefix is the venv root (set by venv activation); avoid
    .resolve() on sys.executable, which follows the symlink to /usr/bin.
    """
    venv_bin = Path(sys.prefix) / "bin"
    path = os.pathsep.join(
        [str(venv_bin), "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/bin"]
    )
    ANSIBLE_LOCAL_TEMP.mkdir(parents=True, exist_ok=True)
    env: dict[str, str] = {
        "PATH": path,
        "ANSIBLE_CONFIG": str(PROJECT_ROOT / "ansible.cfg"),
        "ANSIBLE_COLLECTIONS_PATH": str(PROJECT_ROOT / "collections"),
        "ANSIBLE_ROLES_PATH": str(PROJECT_ROOT / "roles"),
        "ANSIBLE_LOCAL_TEMP": str(ANSIBLE_LOCAL_TEMP),
    }
    for key in _ENVVAR_WHITELIST:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


@contextlib.contextmanager
def _scrubbed_environ(allowed: dict[str, str]) -> Iterator[None]:
    """Temporarily replace os.environ with `allowed` so the ansible-runner
    subprocess inherits a clean env (the artifact's `command` file records
    the full env dict — see codex review P1.3). Restores prior state on exit.

    NOT thread-safe; safe for the single-threaded CLI dispatch. ansible-runner
    treats `envvars` as overlay on top of os.environ, so the actual scrub has
    to happen here, not by passing `envvars` alone.
    """
    snapshot = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(allowed)
        yield
    finally:
        os.environ.clear()
        os.environ.update(snapshot)


def run_playbook(
    *,
    action: str,
    env: str,
    playbook: str,
    limit: str | None = None,
    extravars: dict[str, Any] | None = None,
    forks: int = DEFAULT_FORKS,
    quiet: bool = False,
    cmdline: str | None = None,
) -> RunSummary:
    """Invoke an ansible-runner playbook against the vps_runner inventory.

    Hardening:
    - project_dir=PROJECT_ROOT       (playbook path relative to repo root)
    - inventory=absolute path        (no reliance on ansible.cfg default)
    - artifact_dir=runtime/logs/...  (predictable artifact location)
    - ident=run_id                   (per-run artifact subdir)
    - envvars=whitelist              (P1.3 — bounded; ambient env never leaks)
    - PATH includes venv bin         (P1.4 — works without Makefile wrapping)
    - suppress_env_files=True        (avoid env/ file — but ARTIFACT command
                                      still records `envvars`, hence whitelist)
    - rotate_artifacts=10            (bounded retention)
    - forks=20                       (Ansible default is 5; override here)
    """
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = generate_run_id(action, env)
    inv_dir = inventory_path(env)

    playbook_path = PLAYBOOK_DIR / playbook
    if not playbook_path.exists():
        raise VpsRunnerError(f"playbook not found: {playbook_path}")
    # path relative to project_dir (PROJECT_ROOT)
    playbook_rel = playbook_path.relative_to(PROJECT_ROOT).as_posix()

    envvars = _build_runner_envvars()
    runner_kwargs: dict[str, Any] = dict(
        project_dir=str(PROJECT_ROOT),
        playbook=playbook_rel,
        inventory=str(inv_dir),
        artifact_dir=str(ARTIFACT_ROOT),
        ident=run_id,
        limit=limit,
        extravars=extravars or {},
        envvars=envvars,
        suppress_env_files=True,
        rotate_artifacts=DEFAULT_ROTATE_ARTIFACTS,
        forks=forks,
        quiet=quiet,
    )
    if cmdline:
        runner_kwargs["cmdline"] = cmdline
    with _scrubbed_environ(envvars):
        runner = ansible_runner.run(**runner_kwargs)

    hosts = _collect_host_results(runner)
    return RunSummary(
        run_id=run_id,
        action=action,
        env=env,
        status=runner.status,
        rc=runner.rc,
        artifact_dir=str(ARTIFACT_ROOT / run_id),
        hosts=hosts,
    )


def _collect_host_results(runner: ansible_runner.Runner) -> list[HostResult]:
    """Walk Runner.stats to produce structured per-host results."""
    stats = runner.stats or {}
    ok_hosts = set((stats.get("ok") or {}).keys())
    failed_hosts = set((stats.get("failures") or {}).keys())
    unreachable_hosts = set((stats.get("dark") or {}).keys())
    processed = set((stats.get("processed") or {}).keys())

    all_hosts = ok_hosts | failed_hosts | unreachable_hosts | processed

    results: list[HostResult] = []
    for alias in sorted(all_hosts):
        if alias in unreachable_hosts:
            status, msg = "unreachable", _first_event_msg(
                runner, alias, "runner_on_unreachable"
            )
        elif alias in failed_hosts:
            status, msg = "failed", _first_event_msg(
                runner, alias, "runner_on_failed"
            )
        elif alias in ok_hosts:
            status, msg = "ok", ""
        else:
            status, msg = "skipped", ""
        results.append(HostResult(alias=alias, status=status, message=msg))
    return results


def _first_event_msg(
    runner: ansible_runner.Runner, host: str, event_type: str
) -> str:
    """Best-effort extract a one-line error message for a failed/unreachable host."""
    try:
        for event in runner.host_events(host):
            if event.get("event") == event_type:
                result = (event.get("event_data") or {}).get("res") or {}
                return str(
                    result.get("msg")
                    or result.get("module_stderr")
                    or result.get("stderr")
                    or ""
                )[:500]
    except Exception:  # noqa: BLE001 — fallback to empty msg
        pass
    return ""


# ---------------------------------------------------------------------------
# Round 7 — interactive wizard + per-alias local SSH config (operator key)
# ---------------------------------------------------------------------------
#
# These helpers operate purely on the operator's local files (~/.ssh/config.d/
# and ~/.ssh/config). They are independent from the Ansible execution path
# (run_playbook above), which continues to use the automation key
# (vps_runner_defaults.identity_file in group_vars/vps_targets.yml).
# Per plan-2026-05-22.md §2.2 — two-key model.


_INCLUDE_RE = re.compile(r"^\s*Include\s+(.+)$", re.IGNORECASE)


def prompt_new_host(
    env: str, *, defaults: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Interactive wizard for add-host: collect 4 essential fields.

    Returns dict {alias, ip, port, user} ready for core.add_host(...).
    Returns None on abort: non-TTY stdin, EOFError, or KeyboardInterrupt.
    The caller decides the rc (typically 2 for no-TTY, 130 for user abort).
    """
    if not sys.stdin.isatty():
        sys.stderr.write(
            "vps-runner: wizard requires a TTY; use flag mode instead:\n"
            f"  make vps-add-host ALIAS=<alias> IP=<ip> "
            f"[MANAGED_PORT=1156] [MANAGED_USER=ansible] ENV={env}\n"
        )
        return None

    defaults = defaults or {}
    port_default = int(defaults.get("port", 1156))
    user_default = str(defaults.get("user", "ansible"))

    try:
        existing = set(list_aliases(env))
        while True:
            alias = input("Alias [必填]: ").strip()
            try:
                _validate_alias(alias)
            except VpsRunnerError as exc:
                print(f"  ! {exc}")
                continue
            if alias in existing:
                print(f"  ! alias '{alias}' already exists in env={env}; pick another")
                continue
            break

        while True:
            ip = input("IP / hostname [必填]: ").strip()
            try:
                _validate_hostname(ip)
            except VpsRunnerError as exc:
                print(f"  ! {exc}")
                continue
            break

        while True:
            raw = input(f"Managed SSH port [{port_default}]: ").strip() or str(port_default)
            try:
                port = int(raw)
            except ValueError:
                print("  ! port must be an integer")
                continue
            if port == 22:
                print("  ! port=22 not allowed for managed_port (use a non-22 high port)")
                continue
            if not (1024 <= port <= 65535):
                print("  ! port must be 1024..65535")
                continue
            break

        while True:
            user = input(f"Managed SSH user [{user_default}]: ").strip() or user_default
            try:
                _validate_ssh_user(user)
            except VpsRunnerError as exc:
                print(f"  ! {exc}")
                continue
            break
    except (EOFError, KeyboardInterrupt):
        sys.stderr.write("\n(wizard aborted)\n")
        return None

    return {"alias": alias, "ip": ip, "port": port, "user": user}


def write_ssh_config(
    alias: str,
    *,
    hostname: str,
    port: int,
    user: str,
    identity_file: Path | None = None,
    ssh_config_dir: Path | None = None,
) -> Path:
    """Render ssh_config_entry.j2 → <ssh_config_dir>/<alias>.conf (0600).

    Idempotent overwrite: file content is determined by inputs; re-running
    onboard reconverges. Creates ssh_config_dir if missing (mode 0o700 on
    creation; existing dir is not retightened).

    Defaults are resolved at call time (None sentinels) so tests can
    monkeypatch DEFAULT_PERSONAL_IDENTITY_FILE / DEFAULT_SSH_CONFIG_DIR.
    """
    if identity_file is None:
        identity_file = DEFAULT_PERSONAL_IDENTITY_FILE
    if ssh_config_dir is None:
        ssh_config_dir = DEFAULT_SSH_CONFIG_DIR

    try:
        import jinja2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise VpsRunnerError(
            "jinja2 is required for write_ssh_config. "
            "Run: pip install -r requirements.txt"
        ) from exc

    _validate_alias(alias)
    hostname = _validate_hostname(
        hostname.strip() if isinstance(hostname, str) else hostname
    )
    user = _validate_ssh_user(
        user.strip() if isinstance(user, str) else user
    )

    if not SSH_CONFIG_TEMPLATE.exists():
        raise VpsRunnerError(
            f"ssh config template missing: {SSH_CONFIG_TEMPLATE}"
        )

    ssh_config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = ssh_config_dir / f"{alias}.conf"
    _assert_path_in_dir(target, ssh_config_dir)
    template = jinja2.Template(
        SSH_CONFIG_TEMPLATE.read_text(encoding="utf-8")
    )
    content = template.render(
        server={
            "alias": alias,
            "host": hostname,
            "managed_port": port,
            "managed_user": user,
            "identity_file": str(identity_file),
        }
    )

    target.write_text(content, encoding="utf-8")
    target.chmod(0o600)
    return target


def delete_ssh_config(
    alias: str, ssh_config_dir: Path | None = None
) -> bool:
    """Delete <ssh_config_dir>/<alias>.conf if present.

    Returns True iff the file existed and was removed; False otherwise
    (missing file, or unlink failed). Never raises.
    """
    if ssh_config_dir is None:
        ssh_config_dir = DEFAULT_SSH_CONFIG_DIR
    try:
        _validate_alias(alias)
    except VpsRunnerError:
        return False
    target = ssh_config_dir / f"{alias}.conf"
    try:
        _assert_path_in_dir(target, ssh_config_dir)
    except VpsRunnerError:
        return False
    if not target.exists():
        return False
    try:
        target.unlink()
    except OSError:
        return False
    return True


def check_include_directive(
    ssh_config_path: Path | None = None,
) -> bool:
    """True iff ssh_config_path contains an active `Include …config.d/…` line.

    Returns False when the file is missing, unreadable, or only commented
    Include lines exist. Never raises.
    """
    if ssh_config_path is None:
        ssh_config_path = DEFAULT_SSH_MAIN_CONFIG
    if not ssh_config_path.exists():
        return False
    try:
        text = ssh_config_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = _INCLUDE_RE.match(line)
        if not match:
            continue
        for token in match.group(1).strip().split():
            if "config.d/" in token:
                return True
    return False


def get_repo_root() -> Path:
    """Public accessor for tests + CLI."""
    return PROJECT_ROOT
