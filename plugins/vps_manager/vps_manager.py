#!/usr/bin/env python3
"""VPS lifecycle task processor for Ansispire.

The plugin consumes one-shot YAML tasks from runtime/inbox/vps/pending,
dispatches them to action-specific Ansible playbooks, archives a redacted copy
of each task, and maintains runtime/state/vps_inventory.yml as the long-lived
state source.
"""

from __future__ import annotations

import argparse
import copy
import getpass
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only on broken envs
    raise SystemExit("PyYAML is required. Install project requirements first.") from exc


ALLOWED_ACTIONS = {
    "onboard",
    "recover",
    "modify",
    "remove",
    "audit",
    "docker_host",
    "deploy_compose",
}
ONBOARD_LIKE_ACTIONS = {"onboard", "recover"}
REMOTE_ACTIONS = {"onboard", "recover", "modify", "audit", "docker_host", "deploy_compose"}
PLAYBOOK_BY_ACTION = {
    "recover": "onboard.yml",
}
DEFAULT_ANSIBLE_PYTHON_INTERPRETER = "/usr/bin/python3"
ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
ENV_NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SENSITIVE_KEY_RE = re.compile(r"(^|_)(password|passphrase|token|secret|api[_-]?key)($|_)", re.IGNORECASE)
SAFE_SENSITIVE_KEY_NAMES = {"password_env", "disable_password_login", "password_login_disabled"}
BEGIN_BLOCK = "# BEGIN ANSISPIRE VPS MANAGER\n"
END_BLOCK = "# END ANSISPIRE VPS MANAGER\n"


class VpsManagerError(Exception):
    """Base plugin error."""


class ValidationError(VpsManagerError):
    """Task validation failed."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class PendingIssue:
    path: str
    errors: list[str]


@dataclass(frozen=True)
class ProcessSummary:
    processed: int
    failed: int
    blocked: int
    issues: list[PendingIssue]


@dataclass(frozen=True)
class ActionResult:
    command: list[str]
    returncode: int
    log_path: str | None = None
    skipped_remote: bool = False


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def task_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "task"


def env_name_for_alias(alias: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", alias).strip("_").upper()
    return f"VPS_{normalized}_AUTH"


def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False, ensure_ascii=False)
        handle.write("\n")


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def walk_items(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    items: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            items.extend(walk_items(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(walk_items(child, path + (str(index),)))
    else:
        items.append((path, value))
    return items


def error_messages(error: Exception) -> list[str]:
    if isinstance(error, ValidationError):
        return error.errors
    message = str(error)
    return [message if message else error.__class__.__name__]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key in SAFE_SENSITIVE_KEY_NAMES:
                result[key] = redact(child)
            elif SENSITIVE_KEY_RE.search(key):
                result[key] = "[REDACTED]" if child not in (None, "") else child
            elif key == "private_key" and isinstance(child, str) and "PRIVATE KEY" in child:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact(child)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str) and "-----BEGIN" in value and "PRIVATE KEY" in value:
        return "[REDACTED]"
    return value


class VpsManager:
    """Processes VPS Manager task files."""

    def __init__(
        self,
        root: Path,
        *,
        stable_seconds: float = 2.0,
        dry_run: bool = False,
        no_execute: bool = False,
        timeout: int = 1800,
        prompt_for_passwords: bool = True,
        password_prompt: Callable[[str], str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.plugin_dir = Path(__file__).resolve().parent
        self.runtime_dir = self.root / "runtime"
        self.inbox_dir = self.runtime_dir / "inbox" / "vps"
        self.drafts_dir = self.inbox_dir / "drafts"
        self.pending_dir = self.inbox_dir / "pending"
        self.processing_dir = self.inbox_dir / "processing"
        self.done_dir = self.inbox_dir / "done"
        self.failed_dir = self.inbox_dir / "failed"
        self.cancelled_dir = self.inbox_dir / "cancelled"
        self.archived_dir = self.inbox_dir / "archived"
        self.state_dir = self.runtime_dir / "state"
        self.task_state_dir = self.state_dir / "tasks"
        self.inventory_path = self.state_dir / "vps_inventory.yml"
        self.logs_dir = self.runtime_dir / "logs" / "vps_manager"
        self.stable_seconds = stable_seconds
        self.dry_run = dry_run
        self.no_execute = no_execute
        self.timeout = timeout
        self.prompt_for_passwords = prompt_for_passwords
        self.password_prompt = password_prompt or getpass.getpass
        self.preflight_issues: list[PendingIssue] = []

    def ensure_dirs(self) -> None:
        for path in (
            self.drafts_dir,
            self.pending_dir,
            self.processing_dir,
            self.done_dir,
            self.failed_dir,
            self.cancelled_dir,
            self.archived_dir,
            self.state_dir,
            self.task_state_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def init_runtime(self) -> None:
        self.ensure_dirs()
        if not self.inventory_path.exists():
            write_yaml(self.inventory_path, {"servers": {}})

    def load_inventory(self) -> dict[str, Any]:
        if not self.inventory_path.exists():
            return {"servers": {}}
        data = read_yaml(self.inventory_path)
        if not isinstance(data, dict):
            return {"servers": {}}
        data.setdefault("servers", {})
        return data

    def save_inventory(self, inventory: dict[str, Any]) -> None:
        inventory.setdefault("servers", {})
        write_yaml(self.inventory_path, inventory)

    def pending_files(self) -> list[Path]:
        self.ensure_dirs()
        files = sorted(list(self.pending_dir.glob("*.yml")) + list(self.pending_dir.glob("*.yaml")))
        now = time.time()
        return [path for path in files if now - path.stat().st_mtime >= self.stable_seconds]

    def validate_file(self, path: Path) -> dict[str, Any]:
        task = self.normalize_task(read_yaml(path))
        self.validate_task(task, self.load_inventory(), require_secrets=False)
        return task

    def process_pending(self, limit: int | None = None) -> ProcessSummary:
        self.ensure_dirs()
        pending_paths = self.pending_files()
        if limit is not None:
            pending_paths = pending_paths[:limit]
        return self.process_paths(pending_paths)

    def process_paths(self, pending_paths: list[Path]) -> ProcessSummary:
        self.ensure_dirs()
        self.preflight_issues = []
        self.preflight_issues.extend(self.preflight_pending(pending_paths, require_secrets=False))
        if self.preflight_issues:
            return ProcessSummary(processed=0, failed=0, blocked=len(self.preflight_issues), issues=self.preflight_issues)

        self.prompt_for_missing_passwords(pending_paths)
        self.preflight_issues.extend(self.preflight_pending(pending_paths))
        if self.preflight_issues:
            return ProcessSummary(processed=0, failed=0, blocked=len(self.preflight_issues), issues=self.preflight_issues)

        processed = 0
        failed = 0
        blocked = 0
        for pending_path in pending_paths:
            result = self.process_file(pending_path)
            if result is None:
                continue
            if result == "blocked":
                blocked += 1
                break
            processed += 1
            if result == "failed":
                failed += 1
        return ProcessSummary(processed=processed, failed=failed, blocked=blocked, issues=self.preflight_issues)

    def write_pending_task(self, task: dict[str, Any], *, force: bool = False) -> Path:
        self.ensure_dirs()
        alias = str(task.get("alias") or task.get("kind") or "task")
        path = self.pending_dir / f"{slug(alias)}.yml"
        if path.exists() and not force:
            raise VpsManagerError(f"pending task already exists: {path}; pass --force to overwrite it")
        write_yaml(path, task)
        return path

    def preflight_pending(self, pending_paths: list[Path], *, require_secrets: bool | None = None) -> list[PendingIssue]:
        issues: list[PendingIssue] = []
        inventory = self.load_inventory()
        pending_onboard_aliases: set[str] = set()
        secrets_required = not self.no_execute if require_secrets is None else require_secrets
        for pending_path in pending_paths:
            try:
                task = self.normalize_task(read_yaml(pending_path))
                self.validate_task(task, inventory, require_secrets=secrets_required)
                alias = task.get("alias")
                if task.get("action") in ONBOARD_LIKE_ACTIONS and isinstance(alias, str):
                    if alias in pending_onboard_aliases:
                        raise ValidationError([f"alias {alias} appears in more than one pending onboard/recover task"])
                    pending_onboard_aliases.add(alias)
            except Exception as exc:  # noqa: BLE001 - report all preflight blockers together
                issues.append(PendingIssue(str(pending_path), error_messages(exc)))
        return issues

    def prompt_for_missing_passwords(self, pending_paths: list[Path]) -> None:
        if self.no_execute or not self.can_prompt_for_secrets():
            return

        missing: dict[str, str] = {}
        for pending_path in pending_paths:
            try:
                task = self.normalize_task(read_yaml(pending_path))
            except Exception:  # noqa: BLE001 - normal preflight reports invalid tasks
                continue
            for env_name, label in self.password_env_prompts(task).items():
                if not os.environ.get(env_name):
                    missing.setdefault(env_name, label)

        for env_name, label in sorted(missing.items()):
            secret = self.password_prompt(f"{env_name} for {label} (not saved): ")
            if secret:
                os.environ[env_name] = secret

    def can_prompt_for_secrets(self) -> bool:
        return self.prompt_for_passwords and sys.stdin.isatty()

    @staticmethod
    def password_env_prompts(task: dict[str, Any]) -> dict[str, str]:
        if task.get("action") not in ONBOARD_LIKE_ACTIONS:
            return {}
        auth = task.get("bootstrap", {}).get("auth", {})
        if auth.get("method") != "password":
            return {}
        password_env = auth.get("password_env")
        if not isinstance(password_env, str) or not password_env:
            return {}
        bootstrap = task.get("bootstrap", {})
        label = f"{bootstrap.get('user', 'user')}@{bootstrap.get('host', 'host')}:{bootstrap.get('port', 22)}"
        alias = task.get("alias")
        if isinstance(alias, str) and alias:
            label = f"{alias} ({label})"
        return {password_env: label}

    def process_file(self, pending_path: Path) -> str | None:
        raw_task: Any = None
        lock_path: Path | None = None
        processing_path: Path | None = None
        try:
            raw_task = read_yaml(pending_path)
        except Exception as exc:  # noqa: BLE001 - report parse failures without consuming the task
            self.preflight_issues.append(PendingIssue(str(pending_path), error_messages(exc)))
            return "blocked"

        task_ref = raw_task if isinstance(raw_task, dict) else {}
        task_id = self.make_task_id(task_ref)
        lock_name = str(task_ref.get("alias") or pending_path.stem)
        lock_path = self.acquire_lock(lock_name, task_id)
        if lock_path is None:
            return None

        try:
            task = self.normalize_task(raw_task)
            inventory = self.load_inventory()
            self.validate_task(task, inventory, require_secrets=not self.no_execute)
            processing_path = self.move_to_processing(pending_path, task_id)
            action_result = self.execute_task(task, task_id, inventory)

            effective_dry_run = self.dry_run or bool(task.get("options", {}).get("dry_run", False))
            if not effective_dry_run:
                touched_ssh_paths = self.update_inventory_after_success(task, task_id, inventory)
                if touched_ssh_paths:
                    latest_inventory = self.load_inventory()
                    self.sync_ssh_configs(latest_inventory, touched_ssh_paths)

            self.archive_success(processing_path, task, task_id, action_result)
            return "success"
        except ValidationError as exc:
            self.preflight_issues.append(PendingIssue(str(pending_path), error_messages(exc)))
            return "blocked"
        except Exception as exc:  # noqa: BLE001 - task errors must become failed artefacts
            if processing_path is None:
                self.preflight_issues.append(PendingIssue(str(pending_path), error_messages(exc)))
                return "blocked"
            self.archive_failure(processing_path, raw_task, task_id, exc)
            return "failed"
        finally:
            self.release_lock(lock_path)

    def make_task_id(self, task: dict[str, Any]) -> str:
        action = slug(str(task.get("action") or "unknown"))
        alias = slug(str(task.get("alias") or task.get("kind") or "task"))
        return f"vps-{task_timestamp()}-{alias}-{action}"

    def acquire_lock(self, lock_name: str, task_id: str) -> Path | None:
        self.task_state_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.task_state_dir / f"{slug(lock_name)}.lock"
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return None
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"task_id": task_id, "created_at": utc_now()}) + "\n")
        return lock_path

    @staticmethod
    def release_lock(lock_path: Path | None) -> None:
        if lock_path and lock_path.exists():
            lock_path.unlink()

    def move_to_processing(self, pending_path: Path, task_id: str) -> Path:
        processing_path = self.processing_dir / f"{pending_path.stem}.{task_id}{pending_path.suffix}"
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        pending_path.replace(processing_path)
        return processing_path

    def normalize_task(self, raw_task: Any) -> dict[str, Any]:
        if not isinstance(raw_task, dict):
            raise ValidationError(["task must be a YAML mapping"])

        task = copy.deepcopy(raw_task)
        task.setdefault("options", {})
        action = task.get("action")

        if action in ONBOARD_LIKE_ACTIONS:
            task.setdefault("profile", {})
            task["profile"] = {
                "base_packages": True,
                "unattended_upgrades": True,
                "system_limits": True,
                "swap": False,
                "network_tuning": False,
                "ufw": True,
                "fail2ban": True,
                "docker": False,
                **task["profile"],
            }
            task.setdefault("packages", {})
            task["packages"].setdefault("install", [])
            task["packages"].setdefault("remove", [])
            task.setdefault("swap", {"enabled": False, "size_gb": 1})
            task.setdefault("network_tuning", {"enabled": False})
            task.setdefault("firewall", {})
            ssh_port = task.get("ssh", {}).get("managed_port")
            allowed_ports = task["firewall"].get("allowed_tcp_ports", [ssh_port])
            task["firewall"]["allowed_tcp_ports"] = self.normalize_ports(allowed_ports, task)
            task["firewall"].setdefault("default_incoming", "deny")
            task["firewall"].setdefault("default_outgoing", "allow")
            task["firewall"].setdefault("allow_http_https", False)
            task.setdefault("fail2ban", {"enabled": bool(task["profile"].get("fail2ban", True))})
            task["fail2ban"].setdefault("enabled", bool(task["profile"].get("fail2ban", True)))
            task.setdefault("local", {})
            task["local"].setdefault("write_ssh_config", True)
            task["local"].setdefault("ssh_config_file", "~/.ssh/config.d/ansispire.conf")
            self.normalize_managed_keys(task)
            self.expand_onboard_paths(task)

        if action in {"deploy_compose"}:
            self.expand_compose_paths(task)
            task.setdefault("expose", {})
            if task["expose"].get("mode") in (None, "cloudflare_tunnel"):
                task["expose"].setdefault("mode", "cloudflare_tunnel")
                task["expose"].setdefault("bind_address", "127.0.0.1")

        if action in {"modify"} and isinstance(task.get("changes", {}).get("firewall"), dict):
            firewall = task["changes"]["firewall"]
            firewall["allowed_tcp_ports"] = self.normalize_ports(firewall.get("allowed_tcp_ports", []), task)

        return task

    def expand_onboard_paths(self, task: dict[str, Any]) -> None:
        managed = task.get("managed", {})
        ansible_key = managed.get("ansible_key", {})
        for key in ("public_key", "private_key"):
            if isinstance(ansible_key.get(key), str):
                ansible_key[key] = str(Path(os.path.expanduser(ansible_key[key])).resolve())
        for item in managed.get("personal_keys", []):
            if isinstance(item.get("public_key"), str):
                item["public_key"] = str(Path(os.path.expanduser(item["public_key"])).resolve())
        for item in managed.get("authorized_keys", []):
            if isinstance(item.get("public_key"), str):
                item["public_key"] = str(Path(os.path.expanduser(item["public_key"])).resolve())
        local = task.get("local", {})
        if isinstance(local.get("ssh_config_file"), str):
            local["ssh_config_file"] = str(Path(os.path.expanduser(local["ssh_config_file"])).resolve())
        if isinstance(local.get("ssh_config_identity_file"), str):
            local["ssh_config_identity_file"] = str(Path(os.path.expanduser(local["ssh_config_identity_file"])).resolve())

    def normalize_managed_keys(self, task: dict[str, Any]) -> None:
        managed = task.setdefault("managed", {})
        ansible_key = managed.get("ansible_key")
        if not isinstance(ansible_key, dict):
            ansible_key = {}

        legacy_private_key = managed.get("private_key")
        legacy_public_key = managed.get("public_key")
        if isinstance(legacy_private_key, str) and "private_key" not in ansible_key:
            ansible_key["private_key"] = legacy_private_key
        if isinstance(legacy_public_key, str) and "public_key" not in ansible_key:
            ansible_key["public_key"] = legacy_public_key
        if isinstance(ansible_key.get("private_key"), str) and not ansible_key.get("public_key"):
            ansible_key["public_key"] = f"{ansible_key['private_key']}.pub"
        managed["ansible_key"] = ansible_key

        raw_personal_keys = managed.get("personal_keys", [])
        if raw_personal_keys is None:
            raw_personal_keys = []
        if not isinstance(raw_personal_keys, list):
            raw_personal_keys = [raw_personal_keys]

        personal_keys: list[dict[str, Any]] = []
        for index, item in enumerate(raw_personal_keys, start=1):
            if isinstance(item, str):
                personal_keys.append({"name": f"personal-{index}", "public_key": item})
            elif isinstance(item, dict):
                personal_keys.append(copy.deepcopy(item))
        managed["personal_keys"] = personal_keys

        authorized_keys: list[dict[str, Any]] = []
        if ansible_key.get("public_key"):
            authorized_keys.append({"name": "ansible", "public_key": ansible_key["public_key"], "purpose": "automation"})
        for item in personal_keys:
            if item.get("public_key"):
                entry = copy.deepcopy(item)
                entry.setdefault("purpose", "personal")
                authorized_keys.append(entry)

        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in authorized_keys:
            public_key = item.get("public_key")
            if public_key in seen:
                continue
            seen.add(public_key)
            deduped.append(item)
        managed["authorized_keys"] = deduped

    def expand_compose_paths(self, task: dict[str, Any]) -> None:
        compose = task.get("compose", {})
        for key in ("source", "env_file"):
            value = compose.get(key)
            if isinstance(value, str):
                path = Path(os.path.expanduser(value))
                if not path.is_absolute():
                    path = self.root / path
                compose[key] = str(path.resolve())

    @staticmethod
    def normalize_ports(ports: Any, task: dict[str, Any]) -> list[int]:
        if ports is None:
            return []
        if not isinstance(ports, list):
            ports = [ports]
        managed_port = task.get("ssh", {}).get("managed_port")
        normalized: list[int] = []
        for item in ports:
            value = item
            if isinstance(item, str) and item.strip() == "{{ ssh.managed_port }}":
                value = managed_port
            if isinstance(value, str) and value.isdigit():
                value = int(value)
            normalized.append(value)
        return normalized

    def validate_task(self, task: dict[str, Any], inventory: dict[str, Any], *, require_secrets: bool) -> None:
        errors: list[str] = []

        if task.get("version") != 1:
            errors.append("version must be 1")
        if task.get("kind") != "vps":
            errors.append("kind must be vps")

        action = task.get("action")
        if action not in ALLOWED_ACTIONS:
            errors.append(f"action must be one of: {', '.join(sorted(ALLOWED_ACTIONS))}")

        alias = task.get("alias")
        if action != "audit" or alias is not None:
            self.validate_alias(alias, errors)

        for path, value in walk_items(task):
            key = path[-1] if path else ""
            dotted = ".".join(path)
            if key == "password" and value not in (None, ""):
                errors.append(f"{dotted}: inline password is not allowed; use password_env")
            if key == "private_key" and isinstance(value, str) and "PRIVATE KEY" in value:
                errors.append(f"{dotted}: inline private key material is not allowed; use a file path")

        servers = inventory.get("servers", {})

        if action in ONBOARD_LIKE_ACTIONS:
            self.validate_onboard(task, servers, errors, require_secrets=require_secrets)
        elif action in {"modify", "docker_host", "deploy_compose", "remove"}:
            if isinstance(alias, str) and alias not in servers:
                errors.append(f"alias {alias} is not present in runtime inventory")
        elif action == "audit":
            aliases = task.get("target", {}).get("aliases")
            if not isinstance(aliases, list) or not aliases:
                errors.append("audit target.aliases must be a non-empty list")
            else:
                for item in aliases:
                    self.validate_alias(item, errors, label="target alias")
                    if item not in servers:
                        errors.append(f"alias {item} is not present in runtime inventory")

        if action == "deploy_compose":
            expose = task.get("expose", {})
            mode = expose.get("mode")
            if mode not in {"cloudflare_tunnel", "reverse_proxy", "private", "public"}:
                errors.append("expose.mode must be cloudflare_tunnel, reverse_proxy, private, or public")
            if mode == "public" and not expose.get("public_ports"):
                errors.append("expose.mode public requires expose.public_ports")
            if mode != "public" and expose.get("bind_address") != "127.0.0.1":
                errors.append("non-public compose exposure must bind to 127.0.0.1")
            if not task.get("compose", {}).get("source"):
                errors.append("deploy_compose requires compose.source")

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def validate_alias(alias: Any, errors: list[str], *, label: str = "alias") -> None:
        if not isinstance(alias, str) or not alias:
            errors.append(f"{label} must be a non-empty string")
        elif not ALIAS_RE.match(alias):
            errors.append(f"{label} contains unsupported characters: {alias}")

    def validate_onboard(
        self,
        task: dict[str, Any],
        servers: dict[str, Any],
        errors: list[str],
        *,
        require_secrets: bool,
    ) -> None:
        alias = task.get("alias")
        action = task.get("action")
        if action == "onboard" and isinstance(alias, str) and servers.get(alias, {}).get("status") == "active":
            errors.append(f"alias {alias} already exists and status is active; use modify or recover")
        if action == "recover" and isinstance(alias, str) and alias not in servers:
            errors.append(f"alias {alias} is not present in runtime inventory; use onboard for first install")

        bootstrap = task.get("bootstrap", {})
        if not isinstance(bootstrap.get("host"), str) or not bootstrap.get("host"):
            errors.append("bootstrap.host is required")
        self.validate_port(bootstrap.get("port"), errors, label="bootstrap.port", low=1)
        if not isinstance(bootstrap.get("user"), str) or not bootstrap.get("user"):
            errors.append("bootstrap.user is required")

        auth = bootstrap.get("auth", {})
        method = auth.get("method")
        if method not in {"password", "private_key"}:
            errors.append("bootstrap.auth.method must be password or private_key")
        if method == "password":
            password_env = auth.get("password_env")
            if not isinstance(password_env, str) or not password_env:
                errors.append("bootstrap.auth.password_env is required for password auth")
            elif not ENV_NAME_RE.match(password_env):
                errors.append("bootstrap.auth.password_env must be an uppercase environment variable name, not the password")
            elif require_secrets and not os.environ.get(password_env):
                errors.append(f"environment variable {password_env} is not set")
        if method == "private_key" and not auth.get("private_key"):
            errors.append("bootstrap.auth.private_key is required for private_key auth")
        elif method == "private_key" and require_secrets and not Path(os.path.expanduser(auth["private_key"])).is_file():
            errors.append(f"bootstrap.auth.private_key file does not exist: {auth['private_key']}")

        managed = task.get("managed", {})
        if not isinstance(managed.get("user"), str) or not managed.get("user"):
            errors.append("managed.user is required")
        ansible_key = managed.get("ansible_key", {})
        if not isinstance(ansible_key.get("public_key"), str) or not ansible_key.get("public_key"):
            errors.append("managed.ansible_key.public_key is required")
        if not isinstance(ansible_key.get("private_key"), str) or not ansible_key.get("private_key"):
            errors.append("managed.ansible_key.private_key is required for automation login validation")
        if require_secrets:
            for key in ("private_key", "public_key"):
                path = ansible_key.get(key)
                if isinstance(path, str) and path and not Path(os.path.expanduser(path)).is_file():
                    errors.append(f"managed.ansible_key.{key} file does not exist: {path}")
            for index, item in enumerate(managed.get("personal_keys", [])):
                public_key = item.get("public_key") if isinstance(item, dict) else item
                if isinstance(public_key, str) and public_key and not Path(os.path.expanduser(public_key)).is_file():
                    errors.append(f"managed.personal_keys[{index}].public_key file does not exist: {public_key}")
        if not managed.get("authorized_keys"):
            errors.append("managed.authorized_keys must include at least the Ansible automation key")

        ssh = task.get("ssh", {})
        self.validate_port(ssh.get("managed_port"), errors, label="ssh.managed_port", low=1024)
        if ssh.get("managed_port") == 22:
            errors.append("ssh.managed_port must not be 22")

        for port in task.get("firewall", {}).get("allowed_tcp_ports", []):
            self.validate_port(port, errors, label="firewall.allowed_tcp_ports[]", low=1)

    @staticmethod
    def validate_port(port: Any, errors: list[str], *, label: str, low: int = 1) -> None:
        if not isinstance(port, int):
            errors.append(f"{label} must be an integer")
        elif port < low or port > 65535:
            errors.append(f"{label} must be between {low} and 65535")

    def execute_task(self, task: dict[str, Any], task_id: str, inventory: dict[str, Any]) -> ActionResult:
        action = task["action"]

        if action in ONBOARD_LIKE_ACTIONS and task.get("local", {}).get("update_known_hosts", True):
            self.remove_known_hosts(
                task["bootstrap"]["host"],
                [task["bootstrap"]["port"], task["ssh"]["managed_port"]],
            )

        if self.no_execute:
            return ActionResult(command=[], returncode=0, skipped_remote=True)

        if action == "remove" and not task.get("options", {}).get("touch_remote", False):
            return ActionResult(command=[], returncode=0, skipped_remote=True)

        if action not in REMOTE_ACTIONS and action != "remove":
            return ActionResult(command=[], returncode=0, skipped_remote=True)

        playbook = self.plugin_dir / "playbooks" / PLAYBOOK_BY_ACTION.get(action, f"{action}.yml")
        if not playbook.exists():
            raise VpsManagerError(f"missing playbook for action {action}: {playbook}")

        task_dir = self.task_state_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        inventory_file = task_dir / "inventory.yml"
        vars_file = task_dir / "vars.yml"
        write_yaml(inventory_file, self.build_ansible_inventory(task, inventory))
        write_yaml(vars_file, self.build_ansible_vars(task, task_id))

        command = [
            self.find_ansible_playbook(),
            str(playbook),
            "-i",
            str(inventory_file),
            "-e",
            f"@{vars_file}",
        ]
        if self.dry_run or bool(task.get("options", {}).get("dry_run", False)):
            command.extend(["--check", "--diff"])

        env = os.environ.copy()
        ansible_config = self.root / "ansible.cfg"
        if ansible_config.exists():
            env["ANSIBLE_CONFIG"] = str(ansible_config)
        env.setdefault("ANSIBLE_LOCAL_TEMP", str(self.root / ".ansible" / "tmp"))
        Path(env["ANSIBLE_LOCAL_TEMP"]).mkdir(parents=True, exist_ok=True)
        env["ANSIBLE_REMOTE_TEMP"] = "~/.ansispire-ansible-tmp"

        log_path = self.logs_dir / f"{task_id}.log"
        print(f"==> VPS Manager running {action} for {task.get('alias', '-')}")
        print(f"==> log: {log_path}")
        started_at = time.monotonic()
        proc = subprocess.Popen(
            command,
            cwd=str(self.root),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            with log_path.open("w", encoding="utf-8") as log_handle:
                while True:
                    if proc.stdout is not None:
                        readable, _, _ = select.select([proc.stdout], [], [], 0.2)
                    else:
                        readable = []
                    if readable and proc.stdout is not None:
                        line = proc.stdout.readline()
                        if line:
                            safe_line = self.redact_text(line, task)
                            print(safe_line, end="", flush=True)
                            log_handle.write(safe_line)
                            log_handle.flush()
                    if proc.poll() is not None:
                        if proc.stdout is not None:
                            rest = proc.stdout.read()
                            if rest:
                                safe_rest = self.redact_text(rest, task)
                                print(safe_rest, end="", flush=True)
                                log_handle.write(safe_rest)
                        break
                    if time.monotonic() - started_at > self.timeout:
                        proc.terminate()
                        raise VpsManagerError(f"ansible-playbook timed out after {self.timeout}s; see {log_path}")
        except KeyboardInterrupt as exc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise VpsManagerError(f"ansible-playbook interrupted; see {log_path}") from exc

        if proc.returncode != 0:
            raise VpsManagerError(f"ansible-playbook failed with rc={proc.returncode}; see {log_path}")
        return ActionResult(command=command, returncode=proc.returncode, log_path=str(log_path))

    def find_ansible_playbook(self) -> str:
        local = self.root / ".venv" / "bin" / "ansible-playbook"
        if local.exists():
            return str(local)
        found = shutil.which("ansible-playbook")
        if found:
            return found
        raise VpsManagerError("ansible-playbook not found; run make setup first")

    def build_ansible_inventory(self, task: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
        action = task["action"]
        hostvars: dict[str, Any] = {}

        if action in ONBOARD_LIKE_ACTIONS:
            bootstrap = task["bootstrap"]
            hostvars = {
                "ansible_host": bootstrap["host"],
                "ansible_port": bootstrap["port"],
                "ansible_user": bootstrap["user"],
                "ansible_python_interpreter": task.get("ansible", {}).get(
                    "python_interpreter",
                    DEFAULT_ANSIBLE_PYTHON_INTERPRETER,
                ),
            }
            auth = bootstrap.get("auth", {})
            if auth.get("method") == "password":
                hostvars["ansible_password"] = "{{ lookup('env', '" + auth["password_env"] + "') }}"
            elif auth.get("method") == "private_key":
                hostvars["ansible_ssh_private_key_file"] = str(Path(os.path.expanduser(auth["private_key"])).resolve())
        else:
            target_aliases = self.target_aliases(task)
            servers = inventory.get("servers", {})
            hosts = {}
            for alias in target_aliases:
                server = servers[alias]
                hosts[alias] = {
                    "ansible_host": server["host"],
                    "ansible_port": server["managed_port"],
                    "ansible_user": server["managed_user"],
                    "ansible_python_interpreter": server.get(
                        "ansible_python_interpreter",
                        DEFAULT_ANSIBLE_PYTHON_INTERPRETER,
                    ),
                    "ansible_ssh_private_key_file": str(Path(os.path.expanduser(server.get("ansible_identity_file", server["identity_file"]))).resolve()),
                }
            return {"all": {"children": {"vps_targets": {"hosts": hosts}}}}

        return {"all": {"children": {"vps_targets": {"hosts": {task["alias"]: hostvars}}}}}

    @staticmethod
    def target_aliases(task: dict[str, Any]) -> list[str]:
        if task["action"] == "audit":
            return list(task.get("target", {}).get("aliases", []))
        return [task["alias"]]

    def build_ansible_vars(self, task: dict[str, Any], task_id: str) -> dict[str, Any]:
        return {
            "vps_task_id": task_id,
            "vps_task": task,
            "vps_plugin_dir": str(self.plugin_dir),
            "vps_project_root": str(self.root),
        }

    def redact_text(self, text: str, task: dict[str, Any]) -> str:
        redacted = text
        for path, value in walk_items(task):
            if path and path[-1] == "password_env" and isinstance(value, str):
                secret_value = os.environ.get(value)
                if secret_value:
                    redacted = redacted.replace(secret_value, "[REDACTED]")
        return redacted

    def update_inventory_after_success(
        self,
        task: dict[str, Any],
        task_id: str,
        inventory: dict[str, Any],
    ) -> set[str]:
        action = task["action"]
        servers = inventory.setdefault("servers", {})
        now = utc_now()
        touched_ssh_paths: set[str] = set()

        if action in ONBOARD_LIKE_ACTIONS:
            alias = task["alias"]
            existing = servers.get(alias, {})
            record = {
                "alias": alias,
                "description": task.get("description", ""),
                "host": task["bootstrap"]["host"],
                "bootstrap_port": task["bootstrap"]["port"],
                "managed_port": task["ssh"]["managed_port"],
                "managed_user": task["managed"]["user"],
                "identity_file": task["managed"]["ansible_key"]["private_key"],
                "ansible_identity_file": task["managed"]["ansible_key"]["private_key"],
                "ansible_public_key": task["managed"]["ansible_key"]["public_key"],
                "ansible_python_interpreter": task.get("ansible", {}).get(
                    "python_interpreter",
                    existing.get("ansible_python_interpreter", DEFAULT_ANSIBLE_PYTHON_INTERPRETER),
                ),
                "personal_keys": copy.deepcopy(task["managed"].get("personal_keys", [])),
                "ssh_config_identity_file": task.get("local", {}).get(
                    "ssh_config_identity_file",
                    task["managed"]["ansible_key"]["private_key"],
                ),
                "ssh_config_file": task.get("local", {}).get("ssh_config_file", "~/.ssh/config.d/ansispire.conf"),
                "status": "active",
                "os": existing.get("os", {"family": None, "distribution": None, "version": None}),
                "security": {
                    "root_login_disabled": bool(task["ssh"].get("disable_root_login", True)),
                    "password_login_disabled": bool(task["ssh"].get("disable_password_login", True)),
                    "ufw_enabled": bool(task["profile"].get("ufw", True)),
                    "fail2ban_enabled": bool(task.get("fail2ban", {}).get("enabled", False)),
                },
                "features": copy.deepcopy(task.get("profile", {})),
                "health": {
                    "last_seen": now,
                    "last_audit_status": "unknown",
                    "disk_status": "unknown",
                    "memory_status": "unknown",
                },
                "tasks": {
                    "last_task_id": task_id,
                    "last_action": action,
                    "last_success_at": now,
                },
                "created_at": existing.get("created_at", now),
                "updated_at": now,
            }
            servers[alias] = record
            if task.get("local", {}).get("write_ssh_config", True):
                touched_ssh_paths.add(record["ssh_config_file"])

        elif action == "modify":
            alias = task["alias"]
            server = servers[alias]
            changes = task.get("changes", {})
            if "features" in changes:
                server["features"] = deep_merge(server.get("features", {}), changes["features"])
            server["last_changes"] = changes
            self.mark_task(server, task_id, action, now)

        elif action == "audit":
            for alias in task.get("target", {}).get("aliases", []):
                server = servers[alias]
                server.setdefault("health", {})
                server["health"]["last_seen"] = now
                server["health"]["last_audit_status"] = "ok"
                self.mark_task(server, task_id, action, now)

        elif action == "docker_host":
            alias = task["alias"]
            server = servers[alias]
            server.setdefault("features", {})["docker"] = bool(task.get("docker", {}).get("install", True))
            self.mark_task(server, task_id, action, now)

        elif action == "deploy_compose":
            alias = task["alias"]
            server = servers[alias]
            app = task.get("app", {})
            app_name = app.get("name", "app")
            server.setdefault("apps", {})[app_name] = {
                "project_dir": app.get("project_dir"),
                "expose": copy.deepcopy(task.get("expose", {})),
                "last_deploy_at": now,
                "last_task_id": task_id,
            }
            self.mark_task(server, task_id, action, now)

        elif action == "remove":
            alias = task["alias"]
            existing = servers.get(alias, {})
            ssh_config_file = existing.get("ssh_config_file")
            if ssh_config_file:
                touched_ssh_paths.add(ssh_config_file)

            if task.get("options", {}).get("remove_known_hosts", False) and existing.get("host"):
                self.remove_known_hosts(existing["host"], [existing.get("bootstrap_port", 22), existing.get("managed_port", 22)])

            if task.get("options", {}).get("remove_from_inventory", True):
                servers.pop(alias, None)
            elif alias in servers:
                servers[alias]["status"] = "removed"
                self.mark_task(servers[alias], task_id, action, now)

        self.save_inventory(inventory)
        return touched_ssh_paths

    @staticmethod
    def remove_known_hosts(host: str, ports: list[int]) -> None:
        """Remove old host keys from ~/.ssh/known_hosts to avoid identification errors after reinstall/recover."""
        targets = [host]
        for port in set(ports):
            if port == 22:
                targets.append(host)
            else:
                targets.append(f"[{host}]:{port}")

        for target in sorted(set(targets)):
            try:
                # Quietly remove entries. ssh-keygen -R creates a backup file (~/.ssh/known_hosts.old)
                subprocess.run(["ssh-keygen", "-R", target], capture_output=True, check=False)
            except Exception:  # noqa: BLE001 - ignore failures to find/remove keys
                pass

    @staticmethod
    def mark_task(server: dict[str, Any], task_id: str, action: str, now: str) -> None:
        server["updated_at"] = now
        server.setdefault("tasks", {})
        server["tasks"].update({"last_task_id": task_id, "last_action": action, "last_success_at": now})

    def sync_ssh_configs(self, inventory: dict[str, Any], touched_paths: set[str]) -> None:
        servers = inventory.get("servers", {})
        active_servers = [server for server in servers.values() if server.get("status") == "active"]
        paths = {server.get("ssh_config_file", "~/.ssh/config.d/ansispire.conf") for server in active_servers}
        paths.update(touched_paths)

        for raw_path in paths:
            path = Path(os.path.expanduser(raw_path)).resolve()
            entries = [server for server in active_servers if server.get("ssh_config_file", "~/.ssh/config.d/ansispire.conf") == raw_path]
            block = self.render_ssh_config_block(entries)
            self.replace_managed_block(path, block)

    @staticmethod
    def render_ssh_config_block(servers: list[dict[str, Any]]) -> str:
        if not servers:
            return ""
        lines = [BEGIN_BLOCK]
        for server in sorted(servers, key=lambda item: item["alias"]):
            lines.extend(
                [
                    f"Host {server['alias']}\n",
                    f"  HostName {server['host']}\n",
                    f"  Port {server['managed_port']}\n",
                    f"  User {server['managed_user']}\n",
                    f"  IdentityFile {server.get('ssh_config_identity_file', server['identity_file'])}\n",
                    "  IdentitiesOnly yes\n",
                    "  ServerAliveInterval 30\n",
                    "\n",
                ]
            )
        lines.append(END_BLOCK)
        return "".join(lines)

    @staticmethod
    def replace_managed_block(path: Path, block: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        start = existing.find(BEGIN_BLOCK)
        end = existing.find(END_BLOCK)
        if start != -1 and end != -1:
            end += len(END_BLOCK)
            prefix = existing[:start].rstrip()
            suffix = existing[end:].lstrip()
            parts = [part for part in (prefix, block.rstrip(), suffix.rstrip()) if part]
            new_content = "\n\n".join(parts) + ("\n" if parts else "")
        elif block:
            new_content = existing.rstrip()
            if new_content:
                new_content += "\n\n"
            new_content += block
        else:
            new_content = existing
        path.write_text(new_content, encoding="utf-8")

    def archive_success(
        self,
        processing_path: Path,
        task: dict[str, Any],
        task_id: str,
        result: ActionResult,
    ) -> None:
        done_path = self.done_dir / processing_path.name
        payload = redact(task)
        payload.setdefault("_ansispire", {})
        payload["_ansispire"].update(
            {
                "task_id": task_id,
                "completed_at": utc_now(),
                "result": {
                    "returncode": result.returncode,
                    "skipped_remote": result.skipped_remote,
                    "log_path": result.log_path,
                },
            }
        )
        write_yaml(done_path, payload)
        processing_path.unlink(missing_ok=True)

    def archive_failure(self, processing_path: Path, raw_task: Any, task_id: str, error: Exception) -> None:
        failed_path = self.failed_dir / processing_path.name
        safe_task = redact(raw_task) if isinstance(raw_task, dict) else {
            "source_filename": processing_path.name,
            "raw_task": "[UNPARSEABLE_OR_INVALID]",
        }
        if isinstance(safe_task, dict):
            safe_task.setdefault("_ansispire", {})
            safe_task["_ansispire"].update({"task_id": task_id, "failed_at": utc_now()})
        write_yaml(failed_path, safe_task)

        error_payload = {
            "task_id": task_id,
            "failed_at": utc_now(),
            "error_type": error.__class__.__name__,
            "error": str(error),
        }
        if isinstance(error, ValidationError):
            error_payload["validation_errors"] = error.errors
        write_json(self.failed_dir / f"{processing_path.stem}.error.json", error_payload)
        processing_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ansispire VPS Manager plugin")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2], help="project root")
    parser.add_argument("--stable-seconds", type=float, default=2.0, help="pending file stability window")
    parser.add_argument("--dry-run", action="store_true", help="run Ansible in --check --diff mode")
    parser.add_argument("--no-execute", action="store_true", help="skip remote Ansible execution; useful for local lifecycle tests")
    parser.add_argument("--timeout", type=int, default=1800, help="ansible-playbook timeout in seconds")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create runtime directories and empty inventory")

    process = sub.add_parser("process", help="process stable pending tasks once")
    process.add_argument("--limit", type=int, default=None, help="max tasks to process")

    validate = sub.add_parser("validate", help="validate a task file without moving it")
    validate.add_argument("task_file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manager = VpsManager(
        args.root,
        stable_seconds=args.stable_seconds,
        dry_run=args.dry_run,
        no_execute=args.no_execute,
        timeout=args.timeout,
    )

    if args.command == "init":
        manager.init_runtime()
        print(f"initialized VPS manager runtime under {manager.runtime_dir}")
        return 0

    if args.command == "validate":
        task = manager.validate_file(args.task_file)
        print(f"valid task: action={task.get('action')} alias={task.get('alias', '-')}")
        return 0

    if args.command == "process":
        summary = manager.process_pending(limit=args.limit)
        for issue in summary.issues:
            print(f"blocked: {issue.path}", file=sys.stderr)
            for error in issue.errors:
                print(f"  - {error}", file=sys.stderr)
        print(f"processed={summary.processed} failed={summary.failed} blocked={summary.blocked}")
        return 1 if summary.failed or summary.blocked else 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
