#!/usr/bin/env python3
"""Operator-facing CLI for the VPS Manager plugin."""

from __future__ import annotations

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .vps_manager import VpsManager, env_name_for_alias, read_yaml, slug, task_timestamp, write_yaml


DEFAULT_PACKAGES = [
    "curl",
    "vim",
    "jq",
    "sudo",
    "ufw",
    "fail2ban",
    "unattended-upgrades",
    "bash-completion",
    "git",
    "net-tools",
    "dnsutils",
    "htop",
    "tree",
]

PROFILE_DEFAULTS: dict[str, dict[str, bool]] = {
    "minimal-secure": {
        "base_packages": True,
        "unattended_upgrades": True,
        "system_limits": True,
        "swap": False,
        "network_tuning": False,
        "ufw": True,
        "fail2ban": True,
        "docker": False,
    },
    "web-docker": {
        "base_packages": True,
        "unattended_upgrades": True,
        "system_limits": True,
        "swap": False,
        "network_tuning": False,
        "ufw": True,
        "fail2ban": True,
        "docker": True,
    },
    "tunnel-only": {
        "base_packages": True,
        "unattended_upgrades": True,
        "system_limits": True,
        "swap": False,
        "network_tuning": False,
        "ufw": True,
        "fail2ban": True,
        "docker": False,
    },
    "proxy-node": {
        "base_packages": True,
        "unattended_upgrades": True,
        "system_limits": True,
        "swap": False,
        "network_tuning": True,
        "ufw": True,
        "fail2ban": True,
        "docker": False,
    },
    "custom": {
        "base_packages": True,
        "unattended_upgrades": True,
        "system_limits": True,
        "swap": False,
        "network_tuning": False,
        "ufw": True,
        "fail2ban": True,
        "docker": False,
    },
}

FEATURE_ORDER = [
    "base_packages",
    "unattended_upgrades",
    "system_limits",
    "ufw",
    "fail2ban",
    "swap",
    "network_tuning",
    "docker",
]

ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
RECOVERY_SUPERSEDED_ACTIONS = {"onboard", "recover"}


def prompt_text(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    return ""


def prompt_required(label: str, default: str | None = None) -> str:
    while True:
        value = prompt_text(label, default)
        if value:
            return value
        print(f"{label} is required.", file=sys.stderr)


def prompt_env_name(default: str) -> str:
    while True:
        value = prompt_text("Password environment variable name (not the password)", default)
        if ENV_NAME_RE.match(value):
            return value
        print("Use an uppercase environment variable name, for example VPS_JP_TOKYO_01_AUTH.", file=sys.stderr)


def prompt_int(label: str, default: int, *, low: int = 1, high: int = 65535) -> int:
    while True:
        raw = prompt_text(label, str(default))
        try:
            value = int(raw)
        except ValueError:
            print(f"Enter an integer between {low} and {high}.", file=sys.stderr)
            continue
        if low <= value <= high:
            return value
        print(f"Enter an integer between {low} and {high}.", file=sys.stderr)


def prompt_choice(label: str, choices: list[str], default: str) -> str:
    choice_text = "/".join(choices)
    while True:
        value = prompt_text(f"{label} ({choice_text})", default)
        if value in choices:
            return value
        print(f"Choose one of: {choice_text}", file=sys.stderr)


def prompt_profile(default: str = "minimal-secure") -> str:
    names = list(PROFILE_DEFAULTS)
    default_choice = str(names.index(default) + 1) if default in PROFILE_DEFAULTS else "1"
    print("Profiles:")
    for index, name in enumerate(names, start=1):
        print(f"  {index}. {name}")
    while True:
        raw = prompt_text("Profile", default_choice)
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            return names[int(raw) - 1]
        if raw in PROFILE_DEFAULTS:
            return raw
        print("Choose a profile number or name.", file=sys.stderr)


def prompt_features(profile_name: str, initial: dict[str, Any] | None = None) -> dict[str, bool]:
    features = dict(PROFILE_DEFAULTS[profile_name])
    if initial:
        for key, value in initial.items():
            if key in FEATURE_ORDER:
                features[key] = bool(value)
    while True:
        print("Features:")
        for index, key in enumerate(FEATURE_ORDER, start=1):
            mark = "x" if features.get(key, False) else " "
            print(f"  {index}. [{mark}] {key}")
        raw = prompt_text("Toggle numbers, or press Enter to continue", "")
        if not raw:
            return features
        for item in raw.replace(",", " ").split():
            if item.isdigit() and 1 <= int(item) <= len(FEATURE_ORDER):
                key = FEATURE_ORDER[int(item) - 1]
                features[key] = not features.get(key, False)
            else:
                print(f"Ignoring unknown selection: {item}", file=sys.stderr)


def managed_port_for_alias(alias: str) -> int:
    seed = sum((index + 1) * ord(char) for index, char in enumerate(alias))
    port = 20000 + (seed % 40000)
    return port if port != 22 else 2222


def random_managed_port() -> int:
    return random.SystemRandom().randint(20000, 60999)


def build_onboard_task(
    *,
    action: str = "onboard",
    alias: str,
    host: str,
    bootstrap_user: str,
    bootstrap_port: int,
    auth_method: str,
    password_env: str,
    bootstrap_private_key: str | None,
    managed_user: str,
    managed_port: int,
    profile: dict[str, bool],
    ansible_key_private: str = "~/.ssh/ansispire_ed25519",
    ansible_key_public: str | None = None,
    personal_key_public: str = "~/.ssh/id_ed25519.pub",
    personal_keys: list[dict[str, Any]] | None = None,
    ssh_config_file: str = "~/.ssh/config.d/ansispire.conf",
    ssh_config_identity_file: str = "~/.ssh/id_ed25519",
    description: str = "",
) -> dict[str, Any]:
    if action not in {"onboard", "recover"}:
        raise ValueError("action must be onboard or recover")
    if managed_port == 22:
        raise ValueError("managed SSH port must not be 22")
    if ansible_key_public is None:
        ansible_key_public = f"{ansible_key_private}.pub"
    if personal_keys is None:
        personal_keys = [{"name": "operator", "public_key": personal_key_public}]

    auth: dict[str, Any]
    if auth_method == "password":
        auth = {"method": "password", "password_env": password_env, "private_key": None}
    else:
        auth = {"method": "private_key", "password_env": None, "private_key": bootstrap_private_key}

    return {
        "version": 1,
        "kind": "vps",
        "action": action,
        "alias": alias,
        "description": description,
        "bootstrap": {
            "host": host,
            "port": bootstrap_port,
            "user": bootstrap_user,
            "auth": auth,
        },
        "managed": {
            "user": managed_user,
            "groups": ["sudo", "ssh-users"],
            "shell": "/bin/bash",
            "ansible_key": {
                "private_key": ansible_key_private,
                "public_key": ansible_key_public,
            },
            "personal_keys": [dict(item) for item in personal_keys],
            "sudo": {"nopasswd": True},
        },
        "ssh": {
            "managed_port": managed_port,
            "disable_root_login": True,
            "disable_password_login": True,
            "disable_kbd_interactive": True,
            "allow_groups": ["ssh-users"],
            "close_bootstrap_port_after_success": True,
        },
        "profile": profile,
        "packages": {"install": list(DEFAULT_PACKAGES), "remove": []},
        "swap": {"enabled": bool(profile.get("swap", False)), "size_gb": 1},
        "network_tuning": {
            "enabled": bool(profile.get("network_tuning", False)),
            "bbr": True,
            "tcp_fastopen": False,
            "mtu_probing": True,
        },
        "firewall": {
            "default_incoming": "deny",
            "default_outgoing": "allow",
            "allowed_tcp_ports": ["{{ ssh.managed_port }}"],
            "allow_http_https": bool(profile.get("docker", False)),
        },
        "fail2ban": {
            "enabled": bool(profile.get("fail2ban", True)),
            "sshd": {"bantime": 3600, "findtime": 600, "maxretry": 5},
        },
        "local": {
            "write_ssh_config": True,
            "ssh_config_file": ssh_config_file,
            "ssh_config_identity_file": ssh_config_identity_file,
            "update_known_hosts": True,
        },
        "options": {"force": False, "dry_run": False},
    }


def summarize_task(task: dict[str, Any]) -> str:
    profile = task.get("profile", {})
    lines = [
        "",
        "Summary",
        f"  action:        {task.get('action')}",
        f"  alias:         {task.get('alias')}",
        f"  host:          {task.get('bootstrap', {}).get('host')}",
        f"  bootstrap:     {task.get('bootstrap', {}).get('user')}@{task.get('bootstrap', {}).get('host')}:{task.get('bootstrap', {}).get('port')}",
        f"  auth method:   {task.get('bootstrap', {}).get('auth', {}).get('method')}",
        f"  managed user:  {task.get('managed', {}).get('user')}",
        f"  managed port:  {task.get('ssh', {}).get('managed_port')}",
        "  features:",
    ]
    for key in FEATURE_ORDER:
        mark = "x" if profile.get(key, False) else " "
        lines.append(f"    [{mark}] {key}")
    return "\n".join(lines)


def draft_path_for(manager: VpsManager, task: dict[str, Any]) -> Path:
    alias = slug(str(task.get("alias") or "vps"))
    action = slug(str(task.get("action") or "task"))
    return manager.drafts_dir / f"{alias}.{task_timestamp()}.{action}.yml"


def pending_path_for(manager: VpsManager, task: dict[str, Any]) -> Path:
    alias = slug(str(task.get("alias") or "vps"))
    action = slug(str(task.get("action") or "task"))
    base = manager.pending_dir / f"{alias}.{action}.yml"
    if not base.exists():
        return base
    return manager.pending_dir / f"{alias}.{task_timestamp()}.{action}.yml"


def submit_file(manager: VpsManager, source: Path) -> Path:
    task = manager.validate_file(source)
    pending_path = pending_path_for(manager, task)
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(pending_path))
    return pending_path


def print_process_summary(summary: Any) -> None:
    for issue in summary.issues:
        print(f"blocked: {issue.path}", file=sys.stderr)
        for error in issue.errors:
            print(f"  - {error}", file=sys.stderr)
    print(f"processed={summary.processed} failed={summary.failed} blocked={summary.blocked}")


def process_single_pending(manager: VpsManager, pending_path: Path) -> int:
    summary = manager.process_paths([pending_path])
    print_process_summary(summary)
    return 1 if summary.failed or summary.blocked else 0


def draft_files(manager: VpsManager) -> list[Path]:
    return sorted(manager.drafts_dir.glob("*.yml")) + sorted(manager.drafts_dir.glob("*.yaml"))


def archive_draft(manager: VpsManager, path: Path) -> Path:
    archived_path = manager.archived_dir / path.name
    if archived_path.exists():
        archived_path = archived_path.with_name(f"{archived_path.stem}.{task_timestamp()}{archived_path.suffix}")
    archived_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(archived_path))
    return archived_path


def archive_superseded_drafts(manager: VpsManager, alias: str) -> list[Path]:
    archived: list[Path] = []
    for path in draft_files(manager):
        try:
            task = read_yaml(path)
        except Exception:  # noqa: BLE001 - leave invalid drafts for explicit cleanup
            continue
        if (
            isinstance(task, dict)
            and task.get("alias") == alias
            and task.get("action") in RECOVERY_SUPERSEDED_ACTIONS
        ):
            archived.append(archive_draft(manager, path))
    for path in archived:
        print(f"Archived superseded draft: {path}")
    return archived


def task_label(path: Path) -> str:
    try:
        task = read_yaml(path)
    except Exception:  # noqa: BLE001 - invalid drafts are surfaced by validate when selected directly
        return f"{path} (unreadable)"
    if not isinstance(task, dict):
        return f"{path} (invalid YAML mapping)"
    return f"{path} (action={task.get('action', '-')})"


def resolve_submit_source(manager: VpsManager, selector: str) -> Path:
    source = Path(selector)
    if source.is_file():
        return source
    if not source.is_absolute():
        rooted_source = manager.root / source
        if rooted_source.is_file():
            return rooted_source

    matches: list[Path] = []
    for path in draft_files(manager):
        try:
            task = read_yaml(path)
        except Exception:  # noqa: BLE001 - invalid drafts are not alias matches
            continue
        if not isinstance(task, dict):
            continue
        if task.get("alias") == selector or path.name == selector or path.stem == selector:
            matches.append(path)

    if not matches:
        raise ValueError(f"no draft found for alias or file: {selector}; run make vps-tasks")
    if len(matches) > 1:
        lines = [f"multiple drafts match {selector!r}; submit one explicit file:"]
        lines.extend(f"  - {task_label(path)}" for path in matches)
        lines.append("use: make vps-submit FILE=runtime/inbox/vps/drafts/<draft>.yml")
        raise ValueError("\n".join(lines))
    return matches[0]


def open_editor(path: Path) -> None:
    editor = os.environ.get("EDITOR", "nano")
    subprocess.run([editor, str(path)], check=True)


def personal_keys_from_server(server: dict[str, Any]) -> list[dict[str, Any]]:
    personal_keys = server.get("personal_keys")
    if not isinstance(personal_keys, list) or not personal_keys:
        return []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(personal_keys, start=1):
        if isinstance(item, dict) and isinstance(item.get("public_key"), str):
            entry = dict(item)
            entry.setdefault("name", f"personal-{index}")
            normalized.append(entry)
        elif isinstance(item, str):
            normalized.append({"name": f"personal-{index}", "public_key": item})
    return normalized


def command_new(args: argparse.Namespace) -> int:
    manager = VpsManager(args.root)
    manager.init_runtime()
    action = getattr(args, "action", "onboard")
    inventory = manager.load_inventory()

    def existing_server(alias_value: str | None) -> dict[str, Any]:
        if action != "recover" or not alias_value:
            return {}
        server = inventory.get("servers", {}).get(alias_value)
        return server if isinstance(server, dict) else {}

    if args.non_interactive:
        if not args.alias:
            print("--alias is required with --non-interactive", file=sys.stderr)
            return 2
        alias = args.alias
        existing = existing_server(alias)
        if not args.host and not existing.get("host"):
            print("--host is required with --non-interactive unless recover can reuse inventory host", file=sys.stderr)
            return 2
        host = args.host or existing["host"]
        bootstrap_user = args.bootstrap_user
        bootstrap_port = args.bootstrap_port
        auth_method = args.auth_method
        password_env = args.password_env or env_name_for_alias(alias)
        bootstrap_private_key = args.bootstrap_private_key
        managed_user = args.managed_user or existing.get("managed_user") or "ansible"
        managed_port = args.managed_port or existing.get("managed_port") or managed_port_for_alias(alias)
        if args.profile:
            profile = dict(PROFILE_DEFAULTS[args.profile])
        elif isinstance(existing.get("features"), dict):
            profile = {key: bool(value) for key, value in existing["features"].items() if key in FEATURE_ORDER}
        else:
            profile = dict(PROFILE_DEFAULTS["minimal-secure"])
    else:
        alias = prompt_required("Alias", args.alias)
        existing = existing_server(alias)
        host = prompt_required("VPS host/IP", args.host or existing.get("host"))
        bootstrap_user = prompt_text("Bootstrap user", args.bootstrap_user)
        bootstrap_port = prompt_int("Bootstrap port", args.bootstrap_port)
        auth_method = prompt_choice("Bootstrap auth", ["password", "private_key"], args.auth_method)
        password_env = args.password_env or env_name_for_alias(alias)
        bootstrap_private_key = None
        if auth_method == "password":
            password_env = prompt_env_name(password_env)
        else:
            bootstrap_private_key = prompt_text("Bootstrap private key", "~/.ssh/id_ed25519")
        managed_user = prompt_text("Managed user", args.managed_user or existing.get("managed_user") or "ansible")
        managed_port = prompt_int("Managed SSH port", args.managed_port or existing.get("managed_port") or random_managed_port(), low=1024)
        existing_features = existing.get("features") if isinstance(existing.get("features"), dict) else None
        profile_default = args.profile or ("custom" if existing_features else "minimal-secure")
        profile_name = prompt_profile(profile_default)
        profile = prompt_features(profile_name, existing_features)

    ansible_key_private = args.ansible_key_private or existing.get("ansible_identity_file") or existing.get("identity_file") or "~/.ssh/ansispire_ed25519"
    ansible_key_public = args.ansible_key_public or existing.get("ansible_public_key") or f"{ansible_key_private}.pub"
    existing_personal_keys = personal_keys_from_server(existing)
    personal_key_public = args.personal_public_key or "~/.ssh/id_ed25519.pub"
    personal_keys = None if args.personal_public_key or not existing_personal_keys else existing_personal_keys
    ssh_config_file = args.ssh_config_file or existing.get("ssh_config_file") or "~/.ssh/config.d/ansispire.conf"
    ssh_config_identity_file = args.ssh_config_identity_file or existing.get("ssh_config_identity_file") or "~/.ssh/id_ed25519"

    task = build_onboard_task(
        action=action,
        alias=alias,
        host=host,
        bootstrap_user=bootstrap_user,
        bootstrap_port=bootstrap_port,
        auth_method=auth_method,
        password_env=password_env,
        bootstrap_private_key=bootstrap_private_key,
        managed_user=managed_user,
        managed_port=managed_port,
        profile=profile,
        ansible_key_private=ansible_key_private,
        ansible_key_public=ansible_key_public,
        personal_key_public=personal_key_public,
        personal_keys=personal_keys,
        ssh_config_file=ssh_config_file,
        ssh_config_identity_file=ssh_config_identity_file,
        description=args.description,
    )

    draft_path = draft_path_for(manager, task)
    write_yaml(draft_path, task)
    manager.validate_file(draft_path)
    print(f"Draft written: {draft_path}")
    print(summarize_task(task))

    submit_now = args.submit
    process_now = args.process
    if not args.non_interactive and not submit_now and not process_now:
        choices = ["submit", "edit", "draft", "cancel"]
        default_choice = "draft"
        if action == "recover":
            choices = ["process", "submit", "edit", "draft", "cancel"]
            default_choice = "process"
        while True:
            choice = prompt_choice("Next", choices, default_choice)
            if choice == "process":
                process_now = True
                break
            if choice == "submit":
                submit_now = True
                break
            if choice == "edit":
                open_editor(draft_path)
                manager.validate_file(draft_path)
                print(f"Validated: {draft_path}")
                continue
            if choice == "draft":
                break
            if choice == "cancel":
                cancelled_path = manager.cancelled_dir / draft_path.name
                cancelled_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(draft_path), str(cancelled_path))
                print(f"Cancelled draft: {cancelled_path}")
                return 0

    if submit_now or process_now:
        pending_path = submit_file(manager, draft_path)
        print(f"Submitted to pending: {pending_path}")
        if process_now:
            result = process_single_pending(manager, pending_path)
            if result == 0 and action == "recover":
                archive_superseded_drafts(manager, alias)
            return result
    return 0


def command_submit(args: argparse.Namespace) -> int:
    manager = VpsManager(args.root)
    manager.init_runtime()
    source = resolve_submit_source(manager, args.selector)
    pending_path = submit_file(manager, source)
    print(f"Submitted to pending: {pending_path}")
    return 0


def command_tasks(args: argparse.Namespace) -> int:
    manager = VpsManager(args.root)
    manager.ensure_dirs()
    states = [
        ("drafts", manager.drafts_dir),
        ("pending", manager.pending_dir),
        ("processing", manager.processing_dir),
        ("done", manager.done_dir),
        ("failed", manager.failed_dir),
        ("cancelled", manager.cancelled_dir),
    ]
    rows: list[tuple[str, str, str]] = []
    for state, directory in states:
        for path in sorted(directory.rglob("*.yml")) + sorted(directory.rglob("*.yaml")):
            rows.append((state, path.name, path.relative_to(manager.inbox_dir).as_posix()))

    if not rows:
        print("No VPS Manager tasks found.")
        return 0

    print(f"{'STATE':<12} {'TASK':<54} PATH")
    for state, name, rel_path in rows:
        print(f"{state:<12} {name:<54} {rel_path}")
    return 0


def add_generation_arguments(command: argparse.ArgumentParser, *, profile_default: str | None) -> None:
    command.add_argument("--non-interactive", action="store_true", help="generate from flags instead of prompts")
    command.add_argument("--submit", action="store_true", help="submit generated draft to pending")
    command.add_argument("--process", action="store_true", help="submit generated draft and process only that task immediately")
    command.add_argument("--alias")
    command.add_argument("--host")
    command.add_argument("--description", default="")
    command.add_argument("--bootstrap-user", default="root")
    command.add_argument("--bootstrap-port", type=int, default=22)
    command.add_argument("--auth-method", choices=["password", "private_key"], default="password")
    command.add_argument("--password-env")
    command.add_argument("--bootstrap-private-key")
    command.add_argument("--managed-user")
    command.add_argument("--managed-port", type=int)
    command.add_argument("--profile", choices=list(PROFILE_DEFAULTS), default=profile_default)
    command.add_argument("--ansible-key-private")
    command.add_argument("--ansible-key-public")
    command.add_argument("--personal-public-key")
    command.add_argument("--ssh-config-file")
    command.add_argument("--ssh-config-identity-file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ansispire VPS Manager operator CLI")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="project root")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="interactively create an onboard VPS task draft")
    add_generation_arguments(new, profile_default="minimal-secure")
    new.set_defaults(action="onboard")

    recover = sub.add_parser("recover", help="interactively create a recovery task draft for an existing VPS alias")
    add_generation_arguments(recover, profile_default=None)
    recover.set_defaults(action="recover")

    submit = sub.add_parser("submit", help="move a validated draft task into pending")
    submit.add_argument("selector", help="draft file path, draft filename, or unique draft alias")

    sub.add_parser("tasks", help="list VPS Manager task files by state")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command in {"new", "recover"}:
            return command_new(args)
        if args.command == "submit":
            return command_submit(args)
        if args.command == "tasks":
            return command_tasks(args)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI should print concise operator errors
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
