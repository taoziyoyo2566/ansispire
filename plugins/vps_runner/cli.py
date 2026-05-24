"""vps_runner CLI — user-facing entry point.

Subcommands:
  list      show managed VPS in the given env (sync, no Ansible call)
  audit     probe per-host health via playbooks/audit.yml
  onboard   apply onboard.yml to a single host (idempotent re-onboard supported)
  modify    apply modify.yml with `vps_changes` extravar (packages/ufw/...)
  remove    apply remove.yml (optional) then drop alias from inventory

Each Ansible-running subcommand updates host_vars `vps_runner.last_run` +
`updated_at` after the run via core.record_run().
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from . import vps_runner as core


def _add_env_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--env",
        choices=core.SUPPORTED_ENVS,
        default="dev",
        help="target environment (default: dev)",
    )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _csv_int(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vps-runner",
        description=(
            "Ansible-native VPS lifecycle CLI. Uses ansible-runner + standard "
            "inventory (no inbox, no subprocess wrapping). See plan-2026-05-16."
        ),
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # list
    p_list = subparsers.add_parser(
        "list", help="list managed VPS in the given environment"
    )
    _add_env_arg(p_list)
    p_list.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )

    # audit
    p_audit = subparsers.add_parser(
        "audit", help="probe per-host health (ping, uptime, disk, memory)"
    )
    _add_env_arg(p_audit)
    p_audit.add_argument("--limit", default=None, help="Ansible --limit pattern")
    p_audit.add_argument(
        "--forks", type=int, default=core.DEFAULT_FORKS,
        help=f"Ansible forks (default: {core.DEFAULT_FORKS})",
    )
    p_audit.add_argument(
        "--quiet", action="store_true",
        help="suppress Ansible stdout (artifacts still saved)",
    )

    # onboard
    p_onboard = subparsers.add_parser(
        "onboard",
        help="apply onboard.yml to a single host (creates / refreshes managed config)",
    )
    _add_env_arg(p_onboard)
    p_onboard.add_argument("alias", help="host alias to onboard (must exist in hosts.yml)")
    p_onboard.add_argument(
        "--first-time", action="store_true",
        help=(
            "override connection to vps_runner.bootstrap_user@bootstrap_port for "
            "this run only (use when SSH still uses port 22 / root)"
        ),
    )
    p_onboard.add_argument(
        "--bootstrap-user",
        help="bootstrap user override (defaults to vps_runner.bootstrap_user)",
    )
    p_onboard.add_argument(
        "--bootstrap-port", type=int,
        help="bootstrap port override (defaults to vps_runner.bootstrap_port)",
    )

    # modify
    p_modify = subparsers.add_parser(
        "modify", help="apply ad-hoc changes (packages / firewall / fail2ban)"
    )
    _add_env_arg(p_modify)
    p_modify.add_argument("alias", help="host alias to modify")
    p_modify.add_argument(
        "--add-package", type=_csv, default=[],
        help="comma-separated packages to install",
    )
    p_modify.add_argument(
        "--remove-package", type=_csv, default=[],
        help="comma-separated packages to remove",
    )
    p_modify.add_argument(
        "--add-port", type=_csv_int, default=[],
        help="comma-separated TCP ports to allow in UFW",
    )
    p_modify.add_argument(
        "--remove-port", type=_csv_int, default=[],
        help="comma-separated TCP ports to remove from UFW",
    )
    p_modify.add_argument(
        "--toggle-fail2ban", choices=("on", "off"),
        help="enable or disable fail2ban",
    )

    # add-host (R7: alias is optional; absent → wizard mode)
    p_add = subparsers.add_parser(
        "add-host",
        help=(
            "create a new managed-VPS inventory entry. "
            "With ALIAS+IP → flag mode (R6); without args → interactive wizard."
        ),
    )
    _add_env_arg(p_add)
    p_add.add_argument(
        "alias", nargs="?", default=None,
        help="short alias for the new host (omit → enter wizard mode)",
    )
    p_add.add_argument(
        "--ip", default=None,
        help="ansible_host (IP or DNS name); required in flag mode",
    )
    p_add.add_argument(
        "--port", type=int, default=1156,
        help="managed SSH port (default: 1156; must be 1024-65535, not 22)",
    )
    p_add.add_argument(
        "--user", default="ansible",
        help="managed SSH user (default: ansible)",
    )
    p_add.add_argument(
        "--status", default="pending",
        help="initial vps_runner.status (default: pending; onboard flips to active)",
    )

    # remove
    p_remove = subparsers.add_parser(
        "remove", help="remove alias from inventory (optionally strip sshd drop-ins)"
    )
    _add_env_arg(p_remove)
    p_remove.add_argument("alias", help="host alias to remove")
    p_remove.add_argument(
        "--cleanup-remote", action="store_true",
        help="also run remove.yml to strip Ansispire sshd drop-ins on remote",
    )
    p_remove.add_argument(
        "--yes", action="store_true",
        help="confirm deletion (required — guards against accidental removal)",
    )

    return parser


def _cmd_list(args: argparse.Namespace) -> int:
    hosts = core.list_hosts(args.env)
    if args.format == "json":
        print(json.dumps(hosts, indent=2, default=str))
        return 0

    if not hosts:
        print(f"(no managed VPS in env={args.env})")
        return 0

    headers = ("ALIAS", "HOST", "PORT", "USER", "STATUS", "LAST ACTION", "UPDATED")
    rows = [headers] + [
        (
            h["alias"], h["host"], str(h["port"]), h["user"],
            h["status"], h["last_action"],
            h["updated_at"][:19] if h["updated_at"] else "",
        )
        for h in hosts
    ]
    widths = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    for r in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(r)))
    print(f"\n({len(hosts)} VPS in env={args.env})")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    print(f"==> vps-runner audit env={args.env} limit={args.limit or '*'}")
    try:
        summary = core.run_playbook(
            action="audit", env=args.env, playbook="audit.yml",
            limit=args.limit, forks=args.forks, quiet=args.quiet,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    _print_summary(summary)
    _print_audit_policy(summary)
    return 0 if summary.status == "successful" else 1


def _first_time_extravars(
    bootstrap_user: str,
    bootstrap_port: int,
    *,
    bootstrap_key: str | Path | None = None,
) -> dict[str, Any]:
    extravars: dict[str, Any] = {
        "vps_first_time": True,
        "vps_first_time_user": bootstrap_user,
        "vps_first_time_port": int(bootstrap_port),
    }
    if bootstrap_key:
        extravars["vps_first_time_key"] = str(bootstrap_key)
    return extravars


def _purge_stale_host_keys(host: str | None, *ports: int) -> None:
    """First-time bootstrap pre-step: drop stale ~/.ssh/known_hosts entries for
    the target so an IP-reuse / OS-reinstall host-key change doesn't block SSH.
    StrictHostKeyChecking=no (ansible.cfg) auto-accepts UNKNOWN hosts but still
    hard-fails on a CHANGED key, so the conflicting entry must go before the
    bootstrap connection re-pins the new key. Prints each entry cleared; silent
    when nothing matched."""
    if not host:
        return
    for target in core.clear_known_host(str(host), *ports):
        print(
            f"==> cleared stale known_hosts entry for {target} "
            f"(host key changed/reused — re-pinning on connect)"
        )


def _cmd_onboard(args: argparse.Namespace) -> int:
    alias = args.alias
    try:
        data = core.read_host_vars(args.env, alias)
    except core.VpsRunnerError as exc:
        sys.stderr.write(
            f"vps-runner: {exc}\n"
            f"  → create host_vars/{alias}.yml first; see "
            f"docs/operations/vps-runner.md\n"
        )
        return 2

    extravars: dict[str, Any] = {}
    cmdline_parts: list[str] = []
    if args.first_time:
        vr = data.get("vps_runner") or {}
        boot_user = args.bootstrap_user or vr.get("bootstrap_user", "root")
        boot_port = args.bootstrap_port or vr.get("bootstrap_port", 22)
        managed_host = data.get("ansible_host")
        managed_user = data.get("ansible_user") or vr.get("managed_user")
        try:
            managed_port = int(data.get("ansible_port") or vr.get("managed_port") or 0)
        except (TypeError, ValueError):
            managed_port = 0
        if managed_host and managed_user and managed_port:
            managed_ok, managed_reason = core.ssh_probe(
                managed_host,
                managed_port,
                managed_user,
                core.DEFAULT_AUTOMATION_PRIVATE_KEY,
                timeout=5,
            )
        else:
            managed_ok, managed_reason = False, "managed_vars_missing"
        if managed_ok:
            print(
                "==> managed channel already works; running managed repair mode "
                f"({managed_user}@{managed_port})"
            )
        else:
            # If a previous wizard run failed mid-onboard and persisted the
            # temp bootstrap key path, auto-inject it on retry so the operator
            # doesn't need to re-paste or pass --extra-vars.
            bootstrap_key = vr.get("bootstrap_key")
            extravars = _first_time_extravars(
                boot_user, int(boot_port), bootstrap_key=bootstrap_key,
            )
            if bootstrap_key:
                print(f"==> retry: auto-injecting bootstrap_key={bootstrap_key}")
            print(
                f"==> managed probe failed ({managed_reason}); first-time mode: "
                f"connecting as {boot_user}@{boot_port} "
                f"(host_vars target = {data.get('ansible_user')}@{data.get('ansible_port')})"
            )
            _purge_stale_host_keys(
                data.get("ansible_host"), int(boot_port), managed_port,
            )
    print(f"==> vps-runner onboard alias={alias} env={args.env}")
    try:
        summary = core.run_playbook(
            action="onboard", env=args.env, playbook="onboard.yml",
            limit=alias, extravars=extravars,
            cmdline=" ".join(cmdline_parts) or None,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    _print_summary(summary)
    if summary.status == "successful":
        core.record_run(args.env, alias, summary, set_status="active")
        _clear_bootstrap_key(args.env, alias)
        print(f"==> host_vars/{alias}.yml updated (status=active)")
        _write_local_ssh_alias(args.env, alias)
        return 0
    core.record_run(args.env, alias, summary)
    return 1


def _write_local_ssh_alias(env: str, alias: str) -> None:
    """Post-onboard side-effect: render ssh_config_entry.j2 to
    ~/.ssh/config.d/<alias>.conf using the operator key (DEFAULT_PERSONAL_
    IDENTITY_FILE = ~/.ssh/id_ed25519). Failures are non-fatal — onboard
    already succeeded; SSH alias is convenience.
    """
    try:
        data = core.read_host_vars(env, alias)
        vr = data.get("vps_runner") or {}
        port = int(vr.get("managed_port") or data.get("ansible_port") or 1156)
        user = vr.get("managed_user") or data.get("ansible_user") or "ansible"
        host = data.get("ansible_host") or ""
        if not host:
            sys.stderr.write(
                f"vps-runner: skipping SSH alias write — host_vars/{alias}.yml "
                f"has no ansible_host\n"
            )
            return
        ssh_path = core.write_ssh_config(
            alias, hostname=host, port=port, user=user,
        )
        print(f"==> wrote local SSH alias: {ssh_path}")
        if not core.check_include_directive():
            print(
                "==> note: ~/.ssh/config has no active `Include …config.d/…` line.\n"
                f"    Add this one-liner once so `ssh {alias}` resolves:\n"
                "        Include config.d/*"
            )
    except (core.VpsRunnerError, OSError) as exc:
        sys.stderr.write(f"vps-runner: SSH alias write skipped: {exc}\n")


def _cmd_modify(args: argparse.Namespace) -> int:
    alias = args.alias
    changes: dict[str, Any] = {}
    if args.add_package or args.remove_package:
        changes["packages"] = {
            "install": args.add_package,
            "remove": args.remove_package,
        }
    if args.add_port or args.remove_port:
        changes["firewall"] = {
            "allowed_tcp_ports": {
                "add": args.add_port,
                "remove": args.remove_port,
            }
        }
    if args.toggle_fail2ban:
        changes["fail2ban"] = {"enabled": args.toggle_fail2ban == "on"}

    if not changes:
        sys.stderr.write(
            "vps-runner: no changes specified; pass --add-package / "
            "--remove-package / --add-port / --remove-port / --toggle-fail2ban\n"
        )
        return 64  # EX_USAGE

    try:
        core.read_host_vars(args.env, alias)
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    print(f"==> vps-runner modify alias={alias} env={args.env}")
    print(f"==> changes: {json.dumps(changes)}")
    try:
        summary = core.run_playbook(
            action="modify", env=args.env, playbook="modify.yml",
            limit=alias, extravars={"vps_changes": changes},
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    _print_summary(summary)
    core.record_run(args.env, alias, summary)
    return 0 if summary.status == "successful" else 1


def _handle_existing_add_host_action(
    args: argparse.Namespace, alias: str, action: str
) -> int:
    if action in {"skip", "verified"}:
        return 0
    if action == "repair":
        print(f"==> running managed repair for existing alias '{alias}' ...")
        repair_args = argparse.Namespace(
            alias=alias,
            env=args.env,
            first_time=False,
            bootstrap_user=None,
            bootstrap_port=None,
        )
        return _cmd_onboard(repair_args)
    sys.stderr.write(f"vps-runner: unknown existing-host action: {action}\n")
    return 2


def _cmd_add_host(args: argparse.Namespace) -> int:
    """R11: alias-absent → interactive wizard with full bootstrap creds collection
    (auth method + password or key + bootstrap user/port + managed user/port);
    alias-present → flag mode keeps the R6 contract (managed-port-only inventory
    scaffolding; operator runs onboard separately).
    """
    wizard_mode = args.alias is None
    if not wizard_mode:
        return _cmd_add_host_flag_mode(args)

    # ---- wizard mode (R11) ----
    if not sys.stdin.isatty():
        sys.stderr.write(
            "vps-runner: wizard mode requires a TTY.\n"
            f"  Flag mode: python -m plugins.vps_runner.cli add-host <alias> "
            f"--ip <ip> --env {args.env}\n"
        )
        return 2
    collected = core.prompt_new_host(args.env)
    if collected is None:
        return 130

    alias = collected["alias"]
    existing_action = collected.get("existing_action")
    if existing_action:
        return _handle_existing_add_host_action(args, alias, str(existing_action))

    ip = collected["ip"]
    bootstrap_user = collected["user"]
    bootstrap_port = collected["port"]
    managed_user = collected["managed_user"]
    managed_port = collected["managed_port"]
    auth_method = collected["auth_method"]
    ssh_password = collected["ssh_password"]
    sudo_password = collected["sudo_password"]
    private_key_text = collected["private_key_text"]
    overwrite = collected.get("overwrite", False)

    # ---- write inventory ----
    try:
        path = core.add_host(
            args.env, alias,
            ip=ip, port=managed_port, user=managed_user, status=args.status,
            overwrite=overwrite,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    # Wizard collected bootstrap user/port too — persist into host_vars so
    # subsequent `onboard --first-time` retries don't need flag overrides.
    try:
        data = core.read_host_vars(args.env, alias)
        vr = data.setdefault("vps_runner", {})
        vr["bootstrap_user"] = bootstrap_user
        vr["bootstrap_port"] = bootstrap_port
        core.write_host_vars(args.env, alias, data)
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: bootstrap fields persist failed: {exc}\n")
        return 2

    print(f"==> created {path}")
    print(f"==> added '{alias}' to inventory/vps_runner/{args.env}/hosts.yml")

    # ---- run onboard ----
    if auth_method == "k":
        return _wizard_onboard_key_branch(
            args, alias, ip,
            bootstrap_user=bootstrap_user, bootstrap_port=bootstrap_port,
            managed_user=managed_user, managed_port=managed_port,
            private_key_text=private_key_text or "",
        )

    # ---- password branch: full automatic onboard via passwords dict ----
    extravars = _first_time_extravars(bootstrap_user, int(bootstrap_port))
    cmdline_parts = ["--ask-pass"]
    passwords: dict[str, str] = {
        r"^SSH password:\s*$": ssh_password or "",
    }
    if bootstrap_user != "root":
        cmdline_parts.append("--ask-become-pass")
        passwords[r"^BECOME password.*:\s*$"] = sudo_password or ssh_password or ""

    print(
        f"==> first-time mode: connecting as {bootstrap_user}@{bootstrap_port} "
        f"(host_vars target = {managed_user}@{managed_port})"
    )
    _purge_stale_host_keys(ip, int(bootstrap_port), int(managed_port))
    print(f"==> vps-runner onboard alias={alias} env={args.env}")
    try:
        summary = core.run_playbook(
            action="onboard", env=args.env, playbook="onboard.yml",
            limit=alias, extravars=extravars,
            cmdline=" ".join(cmdline_parts),
            passwords=passwords,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    _print_summary(summary)
    if summary.status == "successful":
        core.record_run(args.env, alias, summary, set_status="active")
        print(f"==> host_vars/{alias}.yml updated (status=active)")
        _write_local_ssh_alias(args.env, alias)
        return 0
    core.record_run(args.env, alias, summary)
    print(
        f"\n==> onboard 失败。inventory 已保留；修复后可重试：\n"
        f"    python -m plugins.vps_runner.cli onboard {alias} "
        f"--env {args.env} --first-time\n"
        f"    （bootstrap user/port 已写入 host_vars，无需 --bootstrap-* flag）"
    )
    return 1


def _wizard_onboard_key_branch(
    args: argparse.Namespace,
    alias: str,
    ip: str,
    *,
    bootstrap_user: str,
    bootstrap_port: int,
    managed_user: str,
    managed_port: int,
    private_key_text: str,
) -> int:
    """R11 T2: key-branch onboard lifecycle.

    1. Write pasted PEM to runtime/keys/vps_runner/<alias>.key (0600)
    2. Run onboard with extravars injecting that path as the SSH key
    3. On success → verify the standard automation key works → cleanup temp key
    4. On failure → keep temp key + persist `vps_runner.bootstrap_key` in
       host_vars so a subsequent `onboard --first-time` retry auto-injects
       the same path without operator re-paste
    """
    try:
        temp_key_path = core.write_temp_key(alias, private_key_text)
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: temp key write failed: {exc}\n")
        return 2
    print(f"==> wrote temp bootstrap key: {temp_key_path}")

    extravars = _first_time_extravars(
        bootstrap_user,
        int(bootstrap_port),
        bootstrap_key=temp_key_path,
    )
    print(
        f"==> first-time mode: connecting as {bootstrap_user}@{bootstrap_port} "
        f"with temp key (host_vars target = {managed_user}@{managed_port})"
    )
    _purge_stale_host_keys(ip, int(bootstrap_port), int(managed_port))
    print(f"==> vps-runner onboard alias={alias} env={args.env}")
    try:
        summary = core.run_playbook(
            action="onboard", env=args.env, playbook="onboard.yml",
            limit=alias, extravars=extravars,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        _persist_bootstrap_key(args.env, alias, temp_key_path)
        return 2

    _print_summary(summary)
    if summary.status != "successful":
        core.record_run(args.env, alias, summary)
        _persist_bootstrap_key(args.env, alias, temp_key_path)
        print(
            f"\n==> onboard 失败. inventory + temp key 保留. 修复后重试:\n"
            f"    python -m plugins.vps_runner.cli onboard {alias} "
            f"--env {args.env} --first-time\n"
            f"    (bootstrap_user/port/key 已记录到 host_vars，无需 --bootstrap-* 或 --extra-vars)"
        )
        return 1

    # ---- onboard succeeded — verify standard automation key now works ----
    print(f"==> verifying standard automation key against {managed_user}@{managed_port}...")
    try:
        verify_summary = core.verify_standard_key(args.env, alias)
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: verify call failed: {exc}\n")
        core.record_run(args.env, alias, summary, set_status="active")
        _persist_bootstrap_key(args.env, alias, temp_key_path)
        print(
            "==> onboard 成功但 verify 没跑成. temp key 保留以备人工检查."
        )
        return 1
    if verify_summary.status != "successful":
        core.record_run(args.env, alias, summary, set_status="active")
        _persist_bootstrap_key(args.env, alias, temp_key_path)
        print(
            "==> verify failed: ansispire_ed25519 against managed user 不通."
            " temp key 保留. 人工排查:\n"
            f"    ssh -i ~/.ssh/ansispire_ed25519 {managed_user}@{ip} "
            f"-p {managed_port}"
        )
        return 1

    # ---- all green — cleanup + finalize ----
    core.record_run(args.env, alias, summary, set_status="active")
    if core.cleanup_temp_key(alias):
        print(f"==> cleaned up temp key {temp_key_path}")
    _clear_bootstrap_key(args.env, alias)
    print(f"==> host_vars/{alias}.yml updated (status=active, bootstrap_key cleared)")
    _write_local_ssh_alias(args.env, alias)
    return 0


def _persist_bootstrap_key(env: str, alias: str, temp_key_path: Path) -> None:
    """Best-effort: write vps_runner.bootstrap_key into host_vars so a
    subsequent `onboard --first-time` retry auto-injects the same temp key.
    Failures are non-fatal (operator can still pass --extra-vars manually)."""
    try:
        data = core.read_host_vars(env, alias)
        data.setdefault("vps_runner", {})["bootstrap_key"] = str(temp_key_path)
        core.write_host_vars(env, alias, data)
    except (core.VpsRunnerError, OSError) as exc:
        sys.stderr.write(
            f"vps-runner: failed to persist bootstrap_key hint: {exc}\n"
        )


def _clear_bootstrap_key(env: str, alias: str) -> None:
    """Set vps_runner.bootstrap_key to null (key retained for schema clarity)."""
    try:
        data = core.read_host_vars(env, alias)
        vr = data.get("vps_runner") or {}
        if "bootstrap_key" in vr:
            vr["bootstrap_key"] = None
            core.write_host_vars(env, alias, data)
    except (core.VpsRunnerError, OSError):
        pass


def _cmd_add_host_flag_mode(args: argparse.Namespace) -> int:
    """R6 contract: alias + --ip given → write inventory only, no onboard."""
    if not args.ip:
        sys.stderr.write(
            "vps-runner: flag mode requires --ip <addr> when alias is given\n"
        )
        return 64
    alias, ip, port, user = args.alias, args.ip, args.port, args.user
    try:
        path = core.add_host(
            args.env, alias,
            ip=ip, port=port, user=user, status=args.status,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2
    print(f"==> created {path}")
    print(f"==> added '{alias}' to inventory/vps_runner/{args.env}/hosts.yml")
    print(
        f"\nNext (after ansispire_ed25519.pub installed on target):\n"
        f"  python -m plugins.vps_runner.cli onboard {alias} "
        f"--env {args.env} --first-time\n"
    )
    return 0


def _cmd_remove(args: argparse.Namespace) -> int:
    alias = args.alias
    if not args.yes:
        sys.stderr.write(
            f"vps-runner: refusing to remove {alias} without --yes\n"
        )
        return 64

    try:
        core.read_host_vars(args.env, alias)
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

    if args.cleanup_remote:
        print(f"==> vps-runner remove alias={alias} env={args.env} (cleanup_remote=true)")
        try:
            summary = core.run_playbook(
                action="remove", env=args.env, playbook="remove.yml",
                limit=alias, extravars={"vps_cleanup_remote": True},
            )
        except core.VpsRunnerError as exc:
            sys.stderr.write(f"vps-runner: {exc}\n")
            return 2
        _print_summary(summary)
        if summary.status != "successful":
            sys.stderr.write(
                "vps-runner: remote cleanup failed; aborting inventory deletion.\n"
                "  → fix the host then rerun, or pass --no-cleanup-remote (TODO) to skip.\n"
            )
            core.record_run(args.env, alias, summary)
            return 1
    else:
        print(f"==> vps-runner remove alias={alias} env={args.env} (cleanup_remote=false)")

    core.remove_alias_from_hosts(args.env, alias)
    core.delete_host_vars(args.env, alias)
    if core.delete_ssh_config(alias):
        print(f"==> removed ~/.ssh/config.d/{alias}.conf")
    print(f"==> {alias} removed from inventory (env={args.env})")
    return 0


def _print_summary(summary: "core.RunSummary") -> None:
    print(f"==> run_id: {summary.run_id}")
    print(f"==> artifact: {summary.artifact_dir}")
    print(f"==> status:   {summary.status} (rc={summary.rc})")
    print()
    print("Host results:")
    if not summary.hosts:
        print("  (no hosts matched the limit pattern)")
    for h in summary.hosts:
        marker = {"ok": "✓", "failed": "✗", "unreachable": "?", "skipped": "-"}.get(
            h.status, "·"
        )
        line = f"  {marker} {h.alias:<20} {h.status}"
        if h.message:
            line += f"  — {h.message.splitlines()[0][:80]}"
        print(line)


def _print_audit_policy(summary: "core.RunSummary") -> None:
    if summary.action != "audit":
        return
    audit_by_alias = core.audit_summary_by_alias(summary)
    if not audit_by_alias:
        return
    print()
    print("Project policy audit:")
    for alias in sorted(audit_by_alias):
        compliance = (audit_by_alias[alias].get("compliance") or {})
        findings = compliance.get("findings") or []
        if not findings:
            print(f"  ✓ {alias}: compliant")
            continue
        print(f"  ✗ {alias}: {len(findings)} finding(s)")
        for finding in findings:
            label = finding.get("label") or finding.get("id") or "unknown"
            expected = " ".join(str(finding.get("expected", "unknown")).split())
            actual = " ".join(str(finding.get("actual", "unknown")).split())
            print(f"      - {label}: expected {expected}; actual {actual[:120]}")


_DISPATCH = {
    "list": _cmd_list,
    "audit": _cmd_audit,
    "onboard": _cmd_onboard,
    "modify": _cmd_modify,
    "remove": _cmd_remove,
    "add-host": _cmd_add_host,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH.get(args.action)
    if handler is None:
        parser.error(f"unknown action: {args.action}")
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
