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
    p_onboard.add_argument(
        "--ask-pass", action="store_true",
        help="prompt for SSH password (use for first-time onboard before key install)",
    )
    p_onboard.add_argument(
        "--ask-become-pass", action="store_true",
        help="prompt for sudo password (use when sudo NOPASSWD not yet configured)",
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

    # add-host
    p_add = subparsers.add_parser(
        "add-host",
        help="create a new managed-VPS inventory entry (host_vars + hosts.yml)",
    )
    _add_env_arg(p_add)
    p_add.add_argument("alias", help="short alias for the new host (e.g. de-d12-1)")
    p_add.add_argument("--ip", required=True, help="ansible_host (IP or DNS name)")
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
    return 0 if summary.status == "successful" else 1


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
        extravars["ansible_user"] = boot_user
        extravars["ansible_port"] = int(boot_port)
        print(
            f"==> first-time mode: connecting as {boot_user}@{boot_port} "
            f"(host_vars target = {data.get('ansible_user')}@{data.get('ansible_port')})"
        )
    if args.ask_pass:
        cmdline_parts.append("--ask-pass")
    if args.ask_become_pass:
        cmdline_parts.append("--ask-become-pass")

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
        print(f"==> host_vars/{alias}.yml updated (status=active)")
        return 0
    core.record_run(args.env, alias, summary)
    return 1


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


def _cmd_add_host(args: argparse.Namespace) -> int:
    try:
        path = core.add_host(
            args.env, args.alias,
            ip=args.ip, port=args.port, user=args.user, status=args.status,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2
    print(f"==> created {path}")
    print(f"==> added '{args.alias}' to inventory/vps_runner/{args.env}/hosts.yml")
    print(
        f"\nNext: vps-runner onboard {args.alias} --env {args.env} "
        f"--first-time --ask-pass\n"
        f"  (add --ask-become-pass if the bootstrap user's sudo requires a password)"
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
