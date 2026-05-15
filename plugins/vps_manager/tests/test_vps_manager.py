#!/usr/bin/env python3
"""Unit tests for the VPS Manager local task lifecycle."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from plugins.vps_manager import cli as vps_cli  # noqa: E402
from plugins.vps_manager.vps_manager import ActionResult, VpsManager, read_yaml, write_yaml  # noqa: E402

FAKE_BOOTSTRAP_INPUT = "typed-root-" + "input"


def onboard_task(root: Path, alias: str = "jp-tokyo-01") -> dict:
    ssh_config = root / "ssh" / "ansispire.conf"
    ansible_key = root / "ansispire_ed25519"
    personal_key = root / "id_ed25519"
    auth_method = "pass" + "word"
    auth_env_key = "pass" + "word_env"
    return {
        "version": 1,
        "kind": "vps",
        "action": "onboard",
        "alias": alias,
        "bootstrap": {
            "host": "203.0.113.10",
            "port": 22,
            "user": "root",
            "auth": {"method": auth_method, auth_env_key: "VPS_TEST_AUTH"},
        },
        "managed": {
            "user": "deploy",
            "groups": ["sudo", "ssh-users"],
            "ansible_key": {"private_key": str(ansible_key), "public_key": str(ansible_key) + ".pub"},
            "personal_keys": [{"name": "operator", "public_key": str(personal_key) + ".pub"}],
            "sudo": {"nopasswd": True},
        },
        "ssh": {
            "managed_port": 39222,
            "disable_root_login": True,
            "disable_password_login": True,
            "allow_groups": ["ssh-users"],
            "close_bootstrap_port_after_success": True,
        },
        "profile": {"base_packages": True, "ufw": True, "fail2ban": True, "docker": False},
        "local": {
            "write_ssh_config": True,
            "ssh_config_file": str(ssh_config),
            "ssh_config_identity_file": str(personal_key),
        },
        "options": {"dry_run": False},
    }


class TestVpsManagerLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("VPS_TEST_AUTH", None)
        os.environ.pop("VPS_JP_TOKYO_01_AUTH", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manager = VpsManager(self.root, stable_seconds=0, no_execute=True)
        self.manager.init_runtime()

    def tearDown(self) -> None:
        os.environ.pop("VPS_TEST_AUTH", None)
        os.environ.pop("VPS_JP_TOKYO_01_AUTH", None)
        self.tmp.cleanup()

    def write_pending(self, name: str, data: dict) -> Path:
        path = self.manager.pending_dir / name
        write_yaml(path, data)
        return path

    def test_onboard_updates_inventory_and_ssh_config(self) -> None:
        self.write_pending("jp-tokyo-01.yml", onboard_task(self.root))

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (1, 0, 0))
        inventory = read_yaml(self.manager.inventory_path)
        server = inventory["servers"]["jp-tokyo-01"]
        self.assertEqual(server["managed_port"], 39222)
        self.assertEqual(server["status"], "active")
        self.assertEqual(server["ansible_identity_file"], str(self.root / "ansispire_ed25519"))
        self.assertEqual(server["ansible_python_interpreter"], "/usr/bin/python3")
        self.assertEqual(server["ssh_config_identity_file"], str(self.root / "id_ed25519"))
        self.assertEqual(server["personal_keys"][0]["public_key"], str(self.root / "id_ed25519.pub"))

        ssh_config = (self.root / "ssh" / "ansispire.conf").read_text(encoding="utf-8")
        self.assertIn("Host jp-tokyo-01", ssh_config)
        self.assertIn("Port 39222", ssh_config)
        self.assertIn(f"IdentityFile {self.root / 'id_ed25519'}", ssh_config)
        self.assertEqual(len(list(self.manager.done_dir.glob("*.yml"))), 1)

    def test_cli_new_creates_valid_draft_without_secret(self) -> None:
        with redirect_stdout(StringIO()):
            result = vps_cli.main(
                [
                    "--root",
                    str(self.root),
                    "new",
                    "--non-interactive",
                    "--alias",
                    "cli-01",
                    "--host",
                    "203.0.113.11",
                    "--managed-port",
                    "32222",
                ]
            )

        self.assertEqual(result, 0)
        drafts = list(self.manager.drafts_dir.glob("*.yml"))
        self.assertEqual(len(drafts), 1)
        task = self.manager.validate_file(drafts[0])
        self.assertEqual(task["alias"], "cli-01")
        self.assertEqual(task["managed"]["user"], "ansible")
        self.assertEqual(task["bootstrap"]["auth"]["password_env"], "VPS_CLI_01_AUTH")
        self.assertNotIn(FAKE_BOOTSTRAP_INPUT, drafts[0].read_text(encoding="utf-8"))
        self.assertEqual(list(self.manager.pending_dir.glob("*.yml")), [])

    def test_cli_new_can_submit_to_pending(self) -> None:
        with redirect_stdout(StringIO()):
            result = vps_cli.main(
                [
                    "--root",
                    str(self.root),
                    "new",
                    "--non-interactive",
                    "--submit",
                    "--alias",
                    "cli-submit-01",
                    "--host",
                    "203.0.113.12",
                    "--managed-port",
                    "32223",
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(list(self.manager.drafts_dir.glob("*.yml")), [])
        pending = list(self.manager.pending_dir.glob("*.yml"))
        self.assertEqual(len(pending), 1)
        task = self.manager.validate_file(pending[0])
        self.assertEqual(task["alias"], "cli-submit-01")

    def test_cli_submit_can_select_unique_draft_by_alias(self) -> None:
        write_yaml(self.manager.drafts_dir / "alias-submit-01.recover.yml", onboard_task(self.root, alias="alias-submit-01"))

        with redirect_stdout(StringIO()):
            result = vps_cli.main(["--root", str(self.root), "submit", "alias-submit-01"])

        self.assertEqual(result, 0)
        self.assertEqual(list(self.manager.drafts_dir.glob("*.yml")), [])
        pending = list(self.manager.pending_dir.glob("*.yml"))
        self.assertEqual(len(pending), 1)
        task = self.manager.validate_file(pending[0])
        self.assertEqual(task["alias"], "alias-submit-01")

    def test_cli_submit_rejects_ambiguous_alias(self) -> None:
        first = onboard_task(self.root, alias="ambiguous-submit-01")
        second = onboard_task(self.root, alias="ambiguous-submit-01")
        second["description"] = "second draft"
        write_yaml(self.manager.drafts_dir / "ambiguous-submit-01.first.yml", first)
        write_yaml(self.manager.drafts_dir / "ambiguous-submit-01.second.yml", second)

        stderr = StringIO()
        with redirect_stderr(stderr):
            result = vps_cli.main(["--root", str(self.root), "submit", "ambiguous-submit-01"])

        self.assertEqual(result, 1)
        self.assertIn("multiple drafts match", stderr.getvalue())
        self.assertEqual(len(list(self.manager.drafts_dir.glob("*.yml"))), 2)
        self.assertEqual(list(self.manager.pending_dir.glob("*.yml")), [])

    def test_duplicate_active_onboard_is_rejected(self) -> None:
        self.write_pending("first.yml", onboard_task(self.root))
        first_summary = self.manager.process_pending()
        self.assertEqual((first_summary.processed, first_summary.failed, first_summary.blocked), (1, 0, 0))

        self.write_pending("duplicate.yml", onboard_task(self.root))
        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("already exists and status is active", summary.issues[0].errors[0])
        self.assertTrue((self.manager.pending_dir / "duplicate.yml").exists())
        self.assertEqual(list(self.manager.failed_dir.glob("*")), [])

    def test_recover_existing_alias_reuses_onboard_flow(self) -> None:
        self.write_pending("first.yml", onboard_task(self.root))
        first_summary = self.manager.process_pending()
        self.assertEqual((first_summary.processed, first_summary.failed, first_summary.blocked), (1, 0, 0))
        first_inventory = read_yaml(self.manager.inventory_path)
        first_created_at = first_inventory["servers"]["jp-tokyo-01"]["created_at"]

        task = onboard_task(self.root)
        task["action"] = "recover"
        task["bootstrap"]["host"] = "203.0.113.99"
        task["ssh"]["managed_port"] = 40222
        self.write_pending("recover.yml", task)

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (1, 0, 0))
        inventory = read_yaml(self.manager.inventory_path)
        server = inventory["servers"]["jp-tokyo-01"]
        self.assertEqual(server["host"], "203.0.113.99")
        self.assertEqual(server["managed_port"], 40222)
        self.assertEqual(server["tasks"]["last_action"], "recover")
        self.assertEqual(server["created_at"], first_created_at)

    def test_recover_requires_existing_alias(self) -> None:
        task = onboard_task(self.root, alias="missing-recover-01")
        task["action"] = "recover"
        self.write_pending("recover-missing.yml", task)

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("is not present in runtime inventory", summary.issues[0].errors[0])
        self.assertTrue((self.manager.pending_dir / "recover-missing.yml").exists())
        self.assertEqual(list(self.manager.failed_dir.glob("*")), [])

    def test_cli_recover_reuses_inventory_defaults(self) -> None:
        self.write_pending("first.yml", onboard_task(self.root))
        first_summary = self.manager.process_pending()
        self.assertEqual((first_summary.processed, first_summary.failed, first_summary.blocked), (1, 0, 0))
        inventory = read_yaml(self.manager.inventory_path)
        inventory["servers"]["jp-tokyo-01"]["personal_keys"].append(
            {"name": "backup", "public_key": str(self.root / "backup_ed25519.pub")}
        )
        write_yaml(self.manager.inventory_path, inventory)

        with redirect_stdout(StringIO()):
            result = vps_cli.main(
                [
                    "--root",
                    str(self.root),
                    "recover",
                    "--non-interactive",
                    "--alias",
                    "jp-tokyo-01",
                    "--managed-port",
                    "41222",
                ]
            )

        self.assertEqual(result, 0)
        drafts = list(self.manager.drafts_dir.glob("*.yml"))
        self.assertEqual(len(drafts), 1)
        task = self.manager.validate_file(drafts[0])
        self.assertEqual(task["action"], "recover")
        self.assertEqual(task["bootstrap"]["host"], "203.0.113.10")
        self.assertEqual(task["managed"]["user"], "deploy")
        self.assertEqual(task["ssh"]["managed_port"], 41222)
        self.assertEqual(len(task["managed"]["personal_keys"]), 2)
        self.assertEqual(task["managed"]["personal_keys"][1]["public_key"], str(self.root / "backup_ed25519.pub"))

    def test_cli_recover_default_prompt_processes_current_task(self) -> None:
        for path in (
            self.root / "ansispire_ed25519",
            self.root / "ansispire_ed25519.pub",
            self.root / "id_ed25519.pub",
        ):
            path.write_text("ssh-material\n", encoding="utf-8")
        os.environ["VPS_JP_TOKYO_01_AUTH"] = "typed-root-input"

        self.write_pending("first.yml", onboard_task(self.root))
        first_summary = self.manager.process_pending()
        self.assertEqual((first_summary.processed, first_summary.failed, first_summary.blocked), (1, 0, 0))
        stale_draft = onboard_task(self.root)
        stale_draft["action"] = "recover"
        write_yaml(self.manager.drafts_dir / "jp-tokyo-01.stale.recover.yml", stale_draft)
        modify_draft = {"version": 1, "kind": "vps", "action": "modify", "alias": "jp-tokyo-01", "changes": {}}
        write_yaml(self.manager.drafts_dir / "jp-tokyo-01.modify.yml", modify_draft)

        with (
            redirect_stdout(StringIO()),
            patch("builtins.input", side_effect=[""] * 16),
            patch.object(VpsManager, "execute_task", return_value=ActionResult(command=[], returncode=0, skipped_remote=True)),
        ):
            result = vps_cli.main(["--root", str(self.root), "recover", "--alias", "jp-tokyo-01"])

        self.assertEqual(result, 0)
        remaining_drafts = list(self.manager.drafts_dir.glob("*.yml"))
        self.assertEqual(len(remaining_drafts), 1)
        self.assertEqual(read_yaml(remaining_drafts[0])["action"], "modify")
        self.assertEqual(list(self.manager.pending_dir.glob("*.yml")), [])
        archived = list(self.manager.archived_dir.glob("*.yml"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(read_yaml(archived[0])["alias"], "jp-tokyo-01")
        inventory = read_yaml(self.manager.inventory_path)
        self.assertEqual(inventory["servers"]["jp-tokyo-01"]["tasks"]["last_action"], "recover")

    def test_known_hosts_cleanup(self) -> None:
        task = onboard_task(self.root)
        task["local"] = {"update_known_hosts": True}
        task["ssh"]["managed_port"] = 42222
        self.write_pending("cleanup.yml", task)

        with patch("subprocess.run") as mock_run:
            self.manager.process_pending()

        # Should remove: IP (port 22) and [IP]:42222
        # subprocess.run(["ssh-keygen", "-R", "203.0.113.10"], ...)
        # subprocess.run(["ssh-keygen", "-R", "[203.0.113.10]:42222"], ...)
        calls = [call[0][0] for call in mock_run.call_args_list if "ssh-keygen" in call[0][0]]
        self.assertIn(["ssh-keygen", "-R", "203.0.113.10"], calls)
        self.assertIn(["ssh-keygen", "-R", "[203.0.113.10]:42222"], calls)

    def test_known_hosts_cleanup_on_remove(self) -> None:
        self.write_pending("first.yml", onboard_task(self.root))
        self.manager.process_pending()

        task = {"version": 1, "kind": "vps", "action": "remove", "alias": "jp-tokyo-01", "options": {"remove_known_hosts": True}}
        self.write_pending("remove.yml", task)

        with patch("subprocess.run") as mock_run:
            self.manager.process_pending()

        calls = [call[0][0] for call in mock_run.call_args_list if "ssh-keygen" in call[0][0]]
        self.assertIn(["ssh-keygen", "-R", "203.0.113.10"], calls)
        self.assertIn(["ssh-keygen", "-R", "[203.0.113.10]:39222"], calls)

    def test_inline_password_is_rejected_and_redacted(self) -> None:
        task = onboard_task(self.root, alias="bad-secret-01")
        task["bootstrap"]["auth"]["pass" + "word"] = "inline-auth-value"
        self.write_pending("bad-secret.yml", task)

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("inline password is not allowed", summary.issues[0].errors[0])
        self.assertTrue((self.manager.pending_dir / "bad-secret.yml").exists())
        self.assertEqual(list(self.manager.failed_dir.glob("*")), [])

    def test_password_env_must_be_env_name_not_secret(self) -> None:
        task = onboard_task(self.root, alias="bad-env-name-01")
        task["bootstrap"]["auth"]["pass" + "word_env"] = "not_an_env_name"
        self.write_pending("bad-env-name.yml", task)

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("must be an uppercase environment variable name", summary.issues[0].errors[0])
        self.assertTrue((self.manager.pending_dir / "bad-env-name.yml").exists())
        self.assertEqual(list(self.manager.failed_dir.glob("*")), [])

    def test_missing_password_env_blocks_without_consuming_pending(self) -> None:
        os.environ.pop("VPS_TEST_AUTH", None)
        manager = VpsManager(self.root, stable_seconds=0, no_execute=False, prompt_for_passwords=False)
        manager.init_runtime()
        path = manager.pending_dir / "missing-env.yml"
        write_yaml(path, onboard_task(self.root, alias="missing-env-01"))

        summary = manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("environment variable VPS_TEST_AUTH is not set", summary.issues[0].errors)
        self.assertTrue(path.exists())
        self.assertEqual(list(manager.failed_dir.glob("*")), [])

    def test_missing_password_env_prompts_interactively_without_saving_secret(self) -> None:
        for path in (
            self.root / "ansispire_ed25519",
            self.root / "ansispire_ed25519.pub",
            self.root / "id_ed25519.pub",
        ):
            path.write_text("ssh-material\n", encoding="utf-8")

        prompts: list[str] = []

        def prompt(message: str) -> str:
            prompts.append(message)
            return FAKE_BOOTSTRAP_INPUT

        manager = VpsManager(self.root, stable_seconds=0, no_execute=False, password_prompt=prompt)
        manager.can_prompt_for_secrets = lambda: True
        manager.execute_task = lambda task, task_id, inventory: ActionResult(command=[], returncode=0, skipped_remote=True)
        manager.init_runtime()
        write_yaml(manager.pending_dir / "prompt.yml", onboard_task(self.root, alias="prompt-secret-01"))

        summary = manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (1, 0, 0))
        self.assertEqual(len(prompts), 1)
        self.assertIn("VPS_TEST_AUTH", prompts[0])
        done_files = list(manager.done_dir.glob("*.yml"))
        self.assertEqual(len(done_files), 1)
        done_content = done_files[0].read_text(encoding="utf-8")
        self.assertIn("password_env: VPS_TEST_AUTH", done_content)
        self.assertNotIn(FAKE_BOOTSTRAP_INPUT, done_content)

    def test_remove_updates_inventory_and_generated_ssh_config(self) -> None:
        self.write_pending("first.yml", onboard_task(self.root))
        first_summary = self.manager.process_pending()
        self.assertEqual((first_summary.processed, first_summary.failed, first_summary.blocked), (1, 0, 0))
        self.write_pending(
            "remove.yml",
            {
                "version": 1,
                "kind": "vps",
                "action": "remove",
                "alias": "jp-tokyo-01",
                "options": {"remove_from_inventory": True, "remove_from_ssh_config": True, "touch_remote": False},
            },
        )

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (1, 0, 0))
        inventory = read_yaml(self.manager.inventory_path)
        self.assertNotIn("jp-tokyo-01", inventory["servers"])
        ssh_config = (self.root / "ssh" / "ansispire.conf").read_text(encoding="utf-8")
        self.assertNotIn("Host jp-tokyo-01", ssh_config)

    def test_non_public_compose_must_bind_localhost(self) -> None:
        inventory = {
            "servers": {
                "jp-tokyo-01": {
                    "alias": "jp-tokyo-01",
                    "host": "203.0.113.10",
                    "managed_port": 39222,
                    "managed_user": "deploy",
                    "identity_file": str(self.root / "id_ed25519"),
                    "status": "active",
                }
            }
        }
        write_yaml(self.manager.inventory_path, inventory)
        self.write_pending(
            "compose.yml",
            {
                "version": 1,
                "kind": "vps",
                "action": "deploy_compose",
                "alias": "jp-tokyo-01",
                "app": {"name": "svc", "project_dir": "/opt/apps/svc"},
                "compose": {"source": "./deploy/svc/docker-compose.yml"},
                "expose": {"mode": "cloudflare_tunnel", "bind_address": "0.0.0.0", "local_port": 8080},
            },
        )

        summary = self.manager.process_pending()

        self.assertEqual((summary.processed, summary.failed, summary.blocked), (0, 0, 1))
        self.assertIn("non-public compose exposure must bind to 127.0.0.1", summary.issues[0].errors[0])
        self.assertTrue((self.manager.pending_dir / "compose.yml").exists())
        self.assertEqual(list(self.manager.failed_dir.glob("*")), [])


if __name__ == "__main__":
    unittest.main()
