"""vps_runner CLI — user-facing entry point.

Subcommands (round 2):
  list   — show managed VPS in the given env (sync, no Ansible call)
  audit  — probe per-host health via playbooks/audit.yml

Subcommands (round 3+):
  onboard / modify / remove
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import vps_runner as core


def _add_env_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--env",
        choices=core.SUPPORTED_ENVS,
        default="dev",
        help="target environment (default: dev)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vps-runner",
        description=(
            "Ansible-native VPS lifecycle CLI. Uses ansible-runner + standard "
            "inventory (no inbox, no subprocess wrapping). See plan-2026-05-16."
        ),
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    p_list = subparsers.add_parser(
        "list",
        help="list managed VPS in the given environment",
    )
    _add_env_arg(p_list)
    p_list.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="output format (default: table)",
    )

    p_audit = subparsers.add_parser(
        "audit",
        help="probe per-host health (ping, uptime, disk, memory)",
    )
    _add_env_arg(p_audit)
    p_audit.add_argument(
        "--limit",
        help=(
            "Ansible --limit pattern (e.g. 'hy-hk-u24' or 'vps_targets' or "
            "'hy-hk-u24,hk-d13'). Defaults to all vps_targets in env."
        ),
        default=None,
    )
    p_audit.add_argument(
        "--forks",
        type=int,
        default=core.DEFAULT_FORKS,
        help=f"Ansible forks (default: {core.DEFAULT_FORKS})",
    )
    p_audit.add_argument(
        "--quiet",
        action="store_true",
        help="suppress Ansible stdout (artifacts still saved)",
    )

    # Placeholder for round 3+
    for stub in ("onboard", "modify", "remove"):
        p = subparsers.add_parser(
            stub,
            help=f"({stub}) — planned for round 3+",
        )
        _add_env_arg(p)

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
            h["alias"],
            h["host"],
            str(h["port"]),
            h["user"],
            h["status"],
            h["last_action"],
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
            action="audit",
            env=args.env,
            playbook="audit.yml",
            limit=args.limit,
            forks=args.forks,
            quiet=args.quiet,
        )
    except core.VpsRunnerError as exc:
        sys.stderr.write(f"vps-runner: {exc}\n")
        return 2

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

    return 0 if summary.status == "successful" else 1


def _cmd_stub_planned(args: argparse.Namespace) -> int:
    sys.stderr.write(
        f"vps-runner: subcommand '{args.action}' is planned for round 3+; "
        "see docs/reviews/feat-vps-manager-v2/plan-2026-05-16.md §4 T3.x\n"
    )
    return 64  # EX_USAGE


_DISPATCH = {
    "list": _cmd_list,
    "audit": _cmd_audit,
    "onboard": _cmd_stub_planned,
    "modify": _cmd_stub_planned,
    "remove": _cmd_stub_planned,
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
