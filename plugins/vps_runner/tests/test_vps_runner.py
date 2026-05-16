"""Tests for plugins.vps_runner — covers core helpers + CLI dispatch + a
single integration test that drives ansible-runner end-to-end against a
deliberately unreachable host to verify status / artifact extraction.

Unit tests use a temp inventory tree (monkeypatched INVENTORY_ROOT) so they
never touch the real inventory/vps_runner/ files.
"""

from __future__ import annotations

import json
import re
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from plugins.vps_runner import cli  # noqa: E402
from plugins.vps_runner import vps_runner as core  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_inventory(tmp_path, monkeypatch):
    """Build a self-contained vps_runner inventory under tmp_path."""
    env = "dev"
    env_dir = tmp_path / "inventory" / "vps_runner" / env
    (env_dir / "host_vars").mkdir(parents=True)
    (env_dir / "hosts.yml").write_text(
        "---\n"
        "all:\n"
        "  children:\n"
        "    vps_targets:\n"
        "      hosts:\n"
        "        alpha:\n"
        "        beta:\n",
        encoding="utf-8",
    )
    (env_dir / "host_vars" / "alpha.yml").write_text(
        "---\n"
        "ansible_host: 192.0.2.1\n"
        "ansible_port: 1156\n"
        "ansible_user: deploy\n"
        "security:\n"
        "  fail2ban_enabled: true\n"
        "vps_runner:\n"
        "  bootstrap_port: 22\n"
        "  bootstrap_user: root\n"
        "  managed_port: 1156\n"
        "  managed_user: deploy\n"
        "  status: active\n"
        "  updated_at: '2026-05-15T00:00:00Z'\n"
        "  last_run:\n"
        "    action: onboard\n",
        encoding="utf-8",
    )
    # beta deliberately has no host_vars — exercises the empty-data path.
    monkeypatch.setattr(core, "INVENTORY_ROOT", tmp_path / "inventory" / "vps_runner")
    return env_dir


# ---------------------------------------------------------------------------
# Unit tests — pure helpers
# ---------------------------------------------------------------------------


def test_generate_run_id_format():
    run_id = core.generate_run_id("audit", "dev")
    assert re.fullmatch(r"vps-runner-\d{8}T\d{6}Z-dev-audit", run_id), run_id


def test_inventory_path_unsupported_env(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "INVENTORY_ROOT", tmp_path)
    with pytest.raises(core.VpsRunnerError, match="unsupported env"):
        core.inventory_path("wrong")


def test_inventory_path_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "INVENTORY_ROOT", tmp_path / "nope")
    with pytest.raises(core.VpsRunnerError, match="inventory directory missing"):
        core.inventory_path("dev")


def test_list_aliases(fake_inventory):
    assert core.list_aliases("dev") == ["alpha", "beta"]


def test_list_hosts_merges_host_vars(fake_inventory):
    hosts = core.list_hosts("dev")
    aliases = {h["alias"] for h in hosts}
    assert aliases == {"alpha", "beta"}
    alpha = next(h for h in hosts if h["alias"] == "alpha")
    assert alpha["host"] == "192.0.2.1"
    assert alpha["port"] == 1156
    assert alpha["user"] == "deploy"
    assert alpha["status"] == "active"
    assert alpha["last_action"] == "onboard"
    beta = next(h for h in hosts if h["alias"] == "beta")
    # No host_vars file → fields default to empty / 'unknown'.
    assert beta["host"] == ""
    assert beta["status"] == "unknown"


def test_read_write_host_vars_roundtrip(fake_inventory):
    data = core.read_host_vars("dev", "alpha")
    assert data["ansible_user"] == "deploy"
    data["vps_runner"]["status"] = "draining"
    core.write_host_vars("dev", "alpha", data)
    fresh = core.read_host_vars("dev", "alpha")
    assert fresh["vps_runner"]["status"] == "draining"


def test_read_host_vars_missing_raises(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="host_vars not found"):
        core.read_host_vars("dev", "gamma")


def test_record_run_updates_last_run_and_status(fake_inventory):
    summary = core.RunSummary(
        run_id="vps-runner-20260516T000000Z-dev-audit",
        action="audit",
        env="dev",
        status="successful",
        rc=0,
        artifact_dir="/tmp/whatever",
        hosts=[],
    )
    core.record_run("dev", "alpha", summary, set_status="active")
    data = core.read_host_vars("dev", "alpha")
    last = data["vps_runner"]["last_run"]
    assert last["id"] == summary.run_id
    assert last["action"] == "audit"
    assert last["status"] == "successful"
    assert last["rc"] == 0
    assert data["vps_runner"]["status"] == "active"
    assert data["vps_runner"]["updated_at"]  # non-empty ISO string


def test_remove_alias_from_hosts_idempotent(fake_inventory):
    assert core.remove_alias_from_hosts("dev", "alpha") is True
    # Second call: alpha already gone → returns False (no change).
    assert core.remove_alias_from_hosts("dev", "alpha") is False
    aliases = core.list_aliases("dev")
    assert "alpha" not in aliases
    assert "beta" in aliases


def test_delete_host_vars_idempotent(fake_inventory):
    assert core.delete_host_vars("dev", "alpha") is True
    assert core.delete_host_vars("dev", "alpha") is False


def test_collect_host_results_classifies_status():
    """Drive _collect_host_results with a fake Runner.stats payload."""
    fake_runner = SimpleNamespace(
        stats={
            "ok": {"alpha": 3},
            "failures": {"beta": 1},
            "dark": {"gamma": 1},
            "processed": {"alpha": 1, "beta": 1, "gamma": 1, "delta": 1},
        },
        host_events=lambda host: [],
    )
    results = core._collect_host_results(fake_runner)
    by_alias = {r.alias: r.status for r in results}
    assert by_alias == {
        "alpha": "ok",
        "beta": "failed",
        "gamma": "unreachable",
        "delta": "skipped",
    }


def test_first_event_msg_extracts_msg():
    fake_runner = SimpleNamespace(
        host_events=lambda host: [
            {"event": "runner_on_start"},
            {
                "event": "runner_on_failed",
                "event_data": {"res": {"msg": "boom!", "stderr": "ignored"}},
            },
        ]
    )
    assert core._first_event_msg(fake_runner, "alpha", "runner_on_failed") == "boom!"


# ---------------------------------------------------------------------------
# CLI dispatch — error paths (no Ansible invocation)
# ---------------------------------------------------------------------------


def test_cli_list_table(fake_inventory, capsys):
    rc = cli.main(["list", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ALIAS" in out
    assert "alpha" in out
    assert "beta" in out


def test_cli_list_json(fake_inventory, capsys):
    rc = cli.main(["list", "--env", "dev", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert {h["alias"] for h in payload} == {"alpha", "beta"}


def test_cli_modify_requires_changes(fake_inventory, capsys):
    rc = cli.main(["modify", "alpha", "--env", "dev"])
    assert rc == 64
    err = capsys.readouterr().err
    assert "no changes specified" in err


def test_cli_modify_unknown_alias(fake_inventory, capsys):
    rc = cli.main(["modify", "missing", "--env", "dev", "--add-package", "vim"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "host_vars not found" in err


def test_cli_remove_requires_yes(fake_inventory, capsys):
    rc = cli.main(["remove", "alpha", "--env", "dev"])
    assert rc == 64
    assert "without --yes" in capsys.readouterr().err


def test_cli_remove_local_only(fake_inventory, capsys):
    rc = cli.main(["remove", "alpha", "--env", "dev", "--yes"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "removed from inventory" in out
    assert "alpha" not in core.list_aliases("dev")


def test_cli_onboard_missing_alias(fake_inventory, capsys):
    rc = cli.main(["onboard", "ghost", "--env", "dev"])
    assert rc == 2
    assert "host_vars not found" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# CLI dispatch — modify happy path with mocked run_playbook
# ---------------------------------------------------------------------------


def test_cli_modify_builds_extravars(fake_inventory, capsys):
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return core.RunSummary(
            run_id="vps-runner-20260516T000000Z-dev-modify",
            action="modify",
            env="dev",
            status="successful",
            rc=0,
            artifact_dir="/tmp/none",
            hosts=[],
        )

    with patch.object(core, "run_playbook", side_effect=fake_run):
        rc = cli.main([
            "modify", "alpha", "--env", "dev",
            "--add-package", "htop,vim",
            "--add-port", "8080,9090",
            "--toggle-fail2ban", "off",
        ])

    assert rc == 0
    assert captured["action"] == "modify"
    assert captured["playbook"] == "modify.yml"
    assert captured["limit"] == "alpha"
    changes = captured["extravars"]["vps_changes"]
    assert changes["packages"] == {"install": ["htop", "vim"], "remove": []}
    assert changes["firewall"] == {
        "allowed_tcp_ports": {"add": [8080, 9090], "remove": []}
    }
    assert changes["fail2ban"] == {"enabled": False}


def test_cli_onboard_first_time_overrides_connection(fake_inventory):
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return core.RunSummary(
            run_id="vps-runner-20260516T000000Z-dev-onboard",
            action="onboard",
            env="dev",
            status="successful",
            rc=0,
            artifact_dir="/tmp/none",
            hosts=[],
        )

    with patch.object(core, "run_playbook", side_effect=fake_run):
        rc = cli.main(["onboard", "alpha", "--env", "dev", "--first-time"])
    assert rc == 0
    extravars = captured["extravars"]
    assert extravars["ansible_user"] == "root"
    assert extravars["ansible_port"] == 22


# ---------------------------------------------------------------------------
# Integration test — drive ansible-runner end-to-end against the REAL repo
# inventory (does NOT need SSH success: 192.0.2.x is RFC 5737 doc-only so
# the host will be unreachable; we assert that ansible-runner classified it
# correctly and produced artifacts).
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_run_playbook_against_unreachable(tmp_path, monkeypatch):
    """Calls run_playbook for real against a tmp inventory whose ansible_host
    points at RFC 5737 documentation space (TEST-NET-1) — guaranteed
    unreachable. Verifies ansible-runner integration produces a RunSummary
    with status='failed' and at least one unreachable host."""
    env_dir = tmp_path / "inventory" / "vps_runner" / "dev"
    (env_dir / "host_vars").mkdir(parents=True)
    (env_dir / "hosts.yml").write_text(
        "---\nall:\n  children:\n    vps_targets:\n      hosts:\n        unreachable-1:\n",
        encoding="utf-8",
    )
    (env_dir / "host_vars" / "unreachable-1.yml").write_text(
        "---\n"
        "ansible_host: 192.0.2.99\n"
        "ansible_port: 22\n"
        "ansible_user: nobody\n"
        "ansible_python_interpreter: /usr/bin/python3\n"
        "ansible_ssh_common_args: '-o ConnectTimeout=3 -o StrictHostKeyChecking=no"
        " -o UserKnownHostsFile=/dev/null -o BatchMode=yes'\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(core, "INVENTORY_ROOT", tmp_path / "inventory" / "vps_runner")
    monkeypatch.setattr(core, "ARTIFACT_ROOT", tmp_path / "artifacts")

    summary = core.run_playbook(
        action="audit",
        env="dev",
        playbook="audit.yml",
        limit="unreachable-1",
        quiet=True,
    )

    assert summary.status in ("failed", "successful"), summary.status
    assert summary.rc != 0, "expected non-zero rc for unreachable host"
    aliases = {h.alias for h in summary.hosts}
    assert "unreachable-1" in aliases
    target = next(h for h in summary.hosts if h.alias == "unreachable-1")
    assert target.status in ("unreachable", "failed"), target.status
    artifact_dir = Path(summary.artifact_dir)
    assert artifact_dir.exists()
    assert (artifact_dir / "status").exists() or (artifact_dir / "stdout").exists()
