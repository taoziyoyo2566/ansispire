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


class VpsRunnerError(Exception):
    """Base plugin error."""


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
    return inventory_path(env) / "host_vars" / f"{alias}.yml"


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
    if not alias or not alias.strip():
        raise VpsRunnerError("alias must be non-empty")
    if not ip or not ip.strip():
        raise VpsRunnerError("ip must be non-empty")
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
    path = host_vars_path(env, alias)
    if not path.exists():
        return False
    path.unlink()
    return True


def list_hosts(env: str) -> list[dict[str, Any]]:
    """Return list of host metadata for the given env (no Ansible call).

    Reads hosts.yml + host_vars/<alias>.yml directly. Cheap, sync, used
    by `vps-runner list`.
    """
    inv_dir = inventory_path(env)
    aliases = list_aliases(env)

    results: list[dict[str, Any]] = []
    host_vars_dir = inv_dir / "host_vars"
    for alias in aliases:
        host_file = host_vars_dir / f"{alias}.yml"
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
    - Forward only a small allowlist of innocuous locale/HOME vars (see
      _ENVVAR_WHITELIST); do NOT pass arbitrary caller env (P1.3).

    Note: sys.prefix is the venv root (set by venv activation); avoid
    .resolve() on sys.executable, which follows the symlink to /usr/bin.
    """
    venv_bin = Path(sys.prefix) / "bin"
    path = os.pathsep.join(
        [str(venv_bin), "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/bin"]
    )
    env: dict[str, str] = {
        "PATH": path,
        "ANSIBLE_CONFIG": str(PROJECT_ROOT / "ansible.cfg"),
        "ANSIBLE_COLLECTIONS_PATH": str(PROJECT_ROOT / "collections"),
        "ANSIBLE_ROLES_PATH": str(PROJECT_ROOT / "roles"),
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


def get_repo_root() -> Path:
    """Public accessor for tests + CLI."""
    return PROJECT_ROOT
