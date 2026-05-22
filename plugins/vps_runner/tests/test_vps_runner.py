"""Tests for plugins.vps_runner — covers core helpers + CLI dispatch + a
single integration test that drives ansible-runner end-to-end against a
deliberately unreachable host to verify status / artifact extraction.

Unit tests use a temp inventory tree (monkeypatched INVENTORY_ROOT) so they
never touch the real inventory/vps_runner/ files.
"""

from __future__ import annotations

import argparse
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


# ---------------------------------------------------------------------------
# add_host — cutover-regression fix (Round 6)
# ---------------------------------------------------------------------------


def test_add_host_creates_host_vars_and_updates_hosts_yml(fake_inventory):
    path = core.add_host(
        "dev", "gamma",
        ip="192.0.2.42", port=1156, user="ansible",
    )
    assert path.exists()
    data = yaml.safe_load(path.read_text())
    assert data["ansible_host"] == "192.0.2.42"
    assert data["ansible_port"] == 1156
    assert data["ansible_user"] == "ansible"
    assert data["vps_runner"]["managed_port"] == 1156
    assert data["vps_runner"]["managed_user"] == "ansible"
    assert data["vps_runner"]["status"] == "pending"
    assert data["vps_runner"]["os"]["family"] is None
    assert "gamma" in core.list_aliases("dev")


def test_add_host_refuses_duplicate_alias(fake_inventory):
    # alpha already exists in fake_inventory
    with pytest.raises(core.VpsRunnerError, match="host_vars already exists"):
        core.add_host("dev", "alpha", ip="192.0.2.99")


def test_add_host_refuses_orphan_alias_in_hosts_yml(fake_inventory):
    # beta is in hosts.yml but has no host_vars file (orphan case).
    # add_host must refuse rather than silently overwrite.
    with pytest.raises(core.VpsRunnerError, match="already in hosts.yml"):
        core.add_host("dev", "beta", ip="192.0.2.99")


def test_add_host_refuses_port_22(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="port=22 not allowed"):
        core.add_host("dev", "gamma", ip="192.0.2.42", port=22)


@pytest.mark.parametrize("bad_port", [0, 1, 1023, 65536, 99999])
def test_add_host_refuses_out_of_range_port(fake_inventory, bad_port):
    with pytest.raises(core.VpsRunnerError, match="out of range"):
        core.add_host("dev", "gamma", ip="192.0.2.42", port=bad_port)


def test_add_host_refuses_empty_alias_or_ip(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="alias must be a non-empty string"):
        core.add_host("dev", "", ip="192.0.2.42")
    with pytest.raises(core.VpsRunnerError, match="hostname must be a non-empty string"):
        core.add_host("dev", "gamma", ip="")


# ---------------------------------------------------------------------------
# F2 — input validators (alias / hostname / ssh user) + path containment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_alias",
    [
        "../foo",          # parent traversal
        "foo/bar",         # path separator
        "/abs/path",       # absolute path
        "..",              # plain traversal
        ".hidden",         # leading dot
        "-flag",           # leading dash (CLI-flag spoof)
        "_under",          # leading underscore (we require alnum-start)
        "foo bar",         # whitespace
        "foo\tbar",        # tab
        "foo\nbar",        # newline (SSH-config injection)
        "foo#bar",         # `#` outside allowed charset
        "foo;rm -rf",      # shell metachars
        "a" * 64,          # over length cap
    ],
)
def test_validate_alias_rejects_bad_input(bad_alias):
    with pytest.raises(core.VpsRunnerError):
        core._validate_alias(bad_alias)


@pytest.mark.parametrize(
    "good_alias",
    [
        "hy-hk-u24",       # existing fleet
        "de-d12-1",
        "test-r7-wizard",
        "A1",              # minimal
        "foo.bar",         # FQDN-ish
        "foo_bar",         # underscore mid-string
        "a" * 63,          # at length cap
    ],
)
def test_validate_alias_accepts_good_input(good_alias):
    assert core._validate_alias(good_alias) == good_alias


def test_validate_alias_rejects_non_str():
    with pytest.raises(core.VpsRunnerError, match="non-empty string"):
        core._validate_alias(None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_host",
    [
        "192.0.2.1\nHost evil",   # newline directive injection
        "192.0.2.1 # comment",    # whitespace + comment
        "foo bar",                # whitespace
        "host#name",              # `#` SSH comment
        "",                       # empty
    ],
)
def test_validate_hostname_rejects_injection(bad_host):
    with pytest.raises(core.VpsRunnerError):
        core._validate_hostname(bad_host)


@pytest.mark.parametrize(
    "good_host",
    [
        "192.0.2.1",
        "203.0.113.42",
        "vps.example.com",
        "::1",                    # IPv6 loopback
        "2001:db8::1",            # IPv6
    ],
)
def test_validate_hostname_accepts_addresses(good_host):
    assert core._validate_hostname(good_host) == good_host


@pytest.mark.parametrize(
    "bad_user",
    [
        "root with space",
        "user;rm",
        "-flag",
        "9starts_digit",          # POSIX: must not start with digit
        "user\nHost evil",
        "",
        "a" * 33,                 # over cap
    ],
)
def test_validate_ssh_user_rejects_bad_input(bad_user):
    with pytest.raises(core.VpsRunnerError):
        core._validate_ssh_user(bad_user)


@pytest.mark.parametrize(
    "good_user",
    ["ansible", "deploy", "_svc", "u1", "ops-bot"],
)
def test_validate_ssh_user_accepts_good_input(good_user):
    assert core._validate_ssh_user(good_user) == good_user


def test_add_host_rejects_traversal_alias(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="invalid"):
        core.add_host("dev", "../evil", ip="192.0.2.99")
    # confirm no file was created outside host_vars
    assert not (fake_inventory.parent / "evil.yml").exists()


def test_add_host_rejects_hostname_injection(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="hostname"):
        core.add_host("dev", "newhost", ip="192.0.2.1\nHost evil")


def test_host_vars_path_blocks_traversal(fake_inventory):
    with pytest.raises(core.VpsRunnerError, match="invalid"):
        core.host_vars_path("dev", "../escape")


def test_write_ssh_config_rejects_traversal_alias(tmp_path):
    with pytest.raises(core.VpsRunnerError, match="invalid"):
        core.write_ssh_config(
            "../escape",
            hostname="192.0.2.1", port=2222, user="ansible",
            ssh_config_dir=tmp_path / "ssh" / "config.d",
        )


def test_write_ssh_config_rejects_hostname_injection(tmp_path):
    with pytest.raises(core.VpsRunnerError, match="hostname"):
        core.write_ssh_config(
            "good-alias",
            hostname="192.0.2.1\n  ProxyCommand /bin/sh",
            port=2222, user="ansible",
            ssh_config_dir=tmp_path / "ssh" / "config.d",
        )


# --- R11/T2 — temp key helpers ----
def test_write_temp_key_creates_0600_normalized(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    pem = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\r\n"
        "blob\r\n"
        "-----END OPENSSH PRIVATE KEY-----"  # no trailing newline
    )
    out = core.write_temp_key("host-x", pem)
    assert out == tmp_path / "tempkeys" / "host-x.key"
    assert oct(out.stat().st_mode)[-3:] == "600"
    text = out.read_text(encoding="utf-8")
    # CRLF normalized + trailing newline ensured
    assert "\r\n" not in text
    assert text.endswith("\n")
    assert "-----BEGIN" in text and "-----END" in text


def test_write_temp_key_rejects_non_pem(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    with pytest.raises(core.VpsRunnerError, match="BEGIN"):
        core.write_temp_key("host-y", "this is not a key")


def test_write_temp_key_rejects_bad_alias(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nx\n-----END OPENSSH PRIVATE KEY-----"
    with pytest.raises(core.VpsRunnerError, match="invalid"):
        core.write_temp_key("../escape", pem)


def test_cleanup_temp_key_idempotent(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    pem = "-----BEGIN OPENSSH PRIVATE KEY-----\nx\n-----END OPENSSH PRIVATE KEY-----"
    core.write_temp_key("zeta", pem)
    assert core.cleanup_temp_key("zeta") is True
    assert core.cleanup_temp_key("zeta") is False  # already gone


def test_cleanup_temp_key_silent_reject_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    # malformed alias → silent False (never-raise contract)
    assert core.cleanup_temp_key("../escape") is False


def test_add_host_overwrite_replaces_existing(fake_inventory):
    # alpha already exists in fake_inventory
    path = core.add_host(
        "dev", "alpha",
        ip="10.1.1.1", port=2222, user="newuser",
        overwrite=True,
    )
    data = yaml.safe_load(path.read_text())
    assert data["ansible_host"] == "10.1.1.1"
    assert data["ansible_port"] == 2222
    assert data["ansible_user"] == "newuser"
    # hosts.yml still has alpha (only one entry, not duplicated)
    assert core.list_aliases("dev").count("alpha") == 1


def test_add_host_overwrite_works_on_fresh_alias(fake_inventory):
    # overwrite=True must be safe even when alias doesn't exist yet
    path = core.add_host(
        "dev", "freshname",
        ip="10.2.2.2", port=2222, user="x",
        overwrite=True,
    )
    assert path.exists()
    assert "freshname" in core.list_aliases("dev")


def test_ssh_probe_identity_file_missing(tmp_path):
    ok, reason = core.ssh_probe(
        "127.0.0.1", 22, "user", tmp_path / "no-such-key",
    )
    assert ok is False
    assert reason.startswith("identity_file_missing:")


def test_verify_existing_schema_fail(fake_inventory):
    # beta has no host_vars file (orphan from fake_inventory)
    ok, msg = core.verify_existing("dev", "beta")
    assert ok is False
    assert "schema" in msg or "unreadable" in msg


def test_alias_collision_menu_option_1_skip(fake_inventory, monkeypatch, capsys):
    inputs = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert core._alias_collision_menu("dev", "alpha") == "skip"


def test_alias_collision_menu_option_2_retry(fake_inventory, monkeypatch):
    inputs = iter(["2"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert core._alias_collision_menu("dev", "alpha") == "retry"


def test_alias_collision_menu_option_3_verified(fake_inventory, monkeypatch):
    inputs = iter(["3"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(core, "verify_existing", lambda env, alias: (True, "OK"))
    assert core._alias_collision_menu("dev", "alpha") == "verified"


def test_alias_collision_menu_option_3_fail_then_overwrite(fake_inventory, monkeypatch):
    inputs = iter(["3", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(
        core, "verify_existing",
        lambda env, alias: (False, "ssh probe failed (permission)"),
    )
    assert core._alias_collision_menu("dev", "alpha") == "overwrite"


def test_alias_collision_menu_option_3_fail_then_decline(fake_inventory, monkeypatch):
    inputs = iter(["3", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr(
        core, "verify_existing",
        lambda env, alias: (False, "ssh probe failed (permission)"),
    )
    assert core._alias_collision_menu("dev", "alpha") == "skip"


def test_alias_collision_menu_option_4_confirmed(fake_inventory, monkeypatch):
    inputs = iter(["4", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert core._alias_collision_menu("dev", "alpha") == "overwrite"


def test_alias_collision_menu_option_4_declined(fake_inventory, monkeypatch):
    inputs = iter(["4", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert core._alias_collision_menu("dev", "alpha") == "skip"


def test_wizard_same_alias_option_1_returns_none(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    # alpha exists; option 1 → wizard returns None
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    inputs = iter(["alpha", "1"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert core.prompt_new_host("dev") is None


def test_wizard_same_alias_option_2_then_new_alias_proceeds(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    inputs = iter([
        "alpha", "2",          # option 2 → retry alias
        "freshhost", "192.0.2.99", "",  # alias / ip / bootstrap_user default
        "k",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "abc",
        "-----END OPENSSH PRIVATE KEY-----",
        "", "", "",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    result = core.prompt_new_host("dev")
    assert result is not None
    assert result["alias"] == "freshhost"
    assert result["overwrite"] is False


def test_wizard_same_alias_option_4_overwrite_flag_propagates(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    inputs = iter([
        "alpha", "4", "y",        # alias collision + menu opt 4 + confirm
        "192.0.2.99",             # ip
        "",                        # bootstrap user (root default)
        "k",                       # auth method
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "abc",
        "-----END OPENSSH PRIVATE KEY-----",
        "", "", "",                # bootstrap port / managed_user / managed_port
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    result = core.prompt_new_host("dev")
    assert result is not None
    assert result["alias"] == "alpha"
    assert result["overwrite"] is True


def test_onboard_first_time_auto_injects_bootstrap_key(
    fake_inventory, monkeypatch, tmp_path
):
    """R11 T2 retry path: if vps_runner.bootstrap_key is set, onboard
    --first-time picks it up and adds ansible_ssh_private_key_file extravar."""
    # seed host_vars with a bootstrap_key value pointing at a fake temp key
    fake_key = tmp_path / "alpha-bootstrap.key"
    fake_key.write_text("dummy", encoding="utf-8")
    data = core.read_host_vars("dev", "alpha")
    data.setdefault("vps_runner", {})["bootstrap_key"] = str(fake_key)
    core.write_host_vars("dev", "alpha", data)

    captured: dict[str, Any] = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return core.RunSummary(
            run_id="vps-runner-mock", action="onboard", env="dev",
            status="failed", rc=4, artifact_dir="/tmp/none", hosts=[],
        )

    with patch.object(core, "run_playbook", side_effect=fake_run):
        rc = cli.main(["onboard", "alpha", "--env", "dev", "--first-time"])
    assert rc == 1
    assert captured["extravars"]["ansible_ssh_private_key_file"] == str(fake_key)


def test_delete_ssh_config_silently_rejects_bad_alias(tmp_path):
    # delete_ssh_config promises never-raise; bad alias → return False
    assert core.delete_ssh_config(
        "../config", ssh_config_dir=tmp_path / "ssh" / "config.d"
    ) is False


def test_list_hosts_fails_loud_on_corrupt_hosts_yml(tmp_path, monkeypatch):
    """R10 — list_hosts must surface hand-edited inventory corruption.

    If hosts.yml is hand-edited to contain a traversal-style alias
    (e.g. `../escape:`), the chokepoint validator must raise so the
    operator sees the corruption immediately, instead of list_hosts
    silently reading a file outside host_vars/ (the R9 contract gap
    reviewer surfaced)."""
    env_dir = tmp_path / "inventory" / "vps_runner" / "dev"
    (env_dir / "host_vars").mkdir(parents=True)
    (env_dir / "hosts.yml").write_text(
        "---\n"
        "all:\n"
        "  children:\n"
        "    vps_targets:\n"
        "      hosts:\n"
        "        ../escape:\n"
        "        legit:\n",
        encoding="utf-8",
    )
    # craft a sibling file that the traversal would target, to prove
    # the validator catches the intent (not just that the file doesn't exist)
    (env_dir / "escape.yml").write_text("---\nansible_host: 10.0.0.99\n")
    (env_dir / "host_vars" / "legit.yml").write_text(
        "---\nansible_host: 192.0.2.1\n"
    )
    monkeypatch.setattr(
        core, "INVENTORY_ROOT", tmp_path / "inventory" / "vps_runner"
    )
    with pytest.raises(core.VpsRunnerError, match="invalid"):
        core.list_hosts("dev")


def test_add_host_cli_dispatch(fake_inventory, capsys):
    rc = cli.main([
        "add-host", "delta",
        "--ip", "192.0.2.50",
        "--env", "dev",
        "--port", "2222",
        "--user", "deploy",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "created" in out
    assert "delta" in out
    # R11 changed flag-mode hint to the full python -m form
    assert "onboard delta --env dev --first-time" in out
    data = yaml.safe_load(core.host_vars_path("dev", "delta").read_text())
    assert data["ansible_port"] == 2222
    assert data["ansible_user"] == "deploy"
    assert data["vps_runner"]["managed_port"] == 2222


def test_add_host_cli_returns_error_on_duplicate(fake_inventory, capsys):
    # alpha already exists; CLI should return rc=2 with stderr message
    rc = cli.main([
        "add-host", "alpha",
        "--ip", "192.0.2.99",
        "--env", "dev",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "host_vars already exists" in err


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


@pytest.mark.integration
def test_integration_run_playbook_without_path(tmp_path, monkeypatch):
    """Reproduces codex review P1.4: caller PATH lacks the venv bin dir, yet
    run_playbook() must still resolve `ansible-playbook` because we inject the
    venv bin into the runner's envvars. Without the fix this returns rc=127
    with stdout 'The command was not found or was not executable: ansible-playbook.'"""
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
    # Strip the venv bin from the caller's PATH — simulates a bare CLI invocation.
    monkeypatch.setenv("PATH", "/usr/local/bin:/usr/bin:/bin")

    summary = core.run_playbook(
        action="audit",
        env="dev",
        playbook="audit.yml",
        limit="unreachable-1",
        quiet=True,
    )
    assert summary.rc != 127, (
        f"expected ansible-playbook to be resolvable; got rc=127 → "
        f"venv bin not injected into envvars PATH"
    )
    aliases = {h.alias for h in summary.hosts}
    assert "unreachable-1" in aliases, (
        f"expected at least one host in stats; got empty set → "
        f"ansible-runner likely failed before reaching the SSH attempt"
    )


# ---------------------------------------------------------------------------
# Round 7 — wizard + local SSH alias write (T1–T15)
# ---------------------------------------------------------------------------


class _FakeStdin:
    """Pretends to be a TTY for isatty() checks. prompt_new_host uses input()
    independently, which we mock via builtins.input — not by reading stdin."""

    def isatty(self):
        return True


def _ssh_dir(tmp_path: Path) -> Path:
    return tmp_path / "ssh" / "config.d"


def _main_ssh(tmp_path: Path) -> Path:
    return tmp_path / "ssh" / "config"


# --- T1 — write_ssh_config renders template, IdentityFile is operator key, 0600
def test_write_ssh_config_renders_template(tmp_path):
    out = core.write_ssh_config(
        "host-a",
        hostname="192.0.2.10",
        port=1156,
        user="ansible",
        ssh_config_dir=_ssh_dir(tmp_path),
    )
    assert out == _ssh_dir(tmp_path) / "host-a.conf"
    text = out.read_text(encoding="utf-8")
    assert "Host host-a" in text
    assert "HostName 192.0.2.10" in text
    assert "Port 1156" in text
    assert "User ansible" in text
    # IdentityFile defaults to the OPERATOR key (~/.ssh/id_ed25519), not the
    # automation key (~/.ssh/ansispire_ed25519). Two-key separation.
    assert "id_ed25519" in text
    assert "ansispire_ed25519" not in text
    assert "IdentitiesOnly yes" in text
    # chmod 0o600
    assert oct(out.stat().st_mode)[-3:] == "600"


# --- T2 — idempotent overwrite (re-render produces identical content)
def test_write_ssh_config_idempotent_overwrite(tmp_path):
    kwargs = dict(
        hostname="192.0.2.20", port=1156, user="ansible",
        ssh_config_dir=_ssh_dir(tmp_path),
    )
    first = core.write_ssh_config("host-b", **kwargs)
    a = first.read_text(encoding="utf-8")
    second = core.write_ssh_config("host-b", **kwargs)
    b = second.read_text(encoding="utf-8")
    assert a == b
    # File was overwritten, not appended.
    assert b.count("Host host-b") == 1


# --- T3 — creates dir with mode 0700 when missing
def test_write_ssh_config_creates_dir_with_mode_0700(tmp_path):
    ssh_d = _ssh_dir(tmp_path)
    assert not ssh_d.exists()
    core.write_ssh_config(
        "host-c", hostname="192.0.2.30", port=1156, user="ansible",
        ssh_config_dir=ssh_d,
    )
    assert ssh_d.is_dir()
    assert oct(ssh_d.stat().st_mode)[-3:] == "700"


# --- T4 — delete returns True when file existed
def test_delete_ssh_config_removes_file(tmp_path):
    ssh_d = _ssh_dir(tmp_path)
    core.write_ssh_config(
        "host-d", hostname="192.0.2.40", port=1156, user="ansible",
        ssh_config_dir=ssh_d,
    )
    target = ssh_d / "host-d.conf"
    assert target.exists()
    assert core.delete_ssh_config("host-d", ssh_config_dir=ssh_d) is True
    assert not target.exists()


# --- T5 — delete is idempotent when file absent
def test_delete_ssh_config_idempotent_when_missing(tmp_path):
    ssh_d = _ssh_dir(tmp_path)
    ssh_d.mkdir(parents=True)
    assert core.delete_ssh_config("ghost", ssh_config_dir=ssh_d) is False


# --- T6 — Include directive detection (active line → True)
def test_check_include_directive_detects_present(tmp_path):
    cfg = _main_ssh(tmp_path)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "Host github.com\n  HostName github.com\n\n"
        "Include config.d/*\n",
        encoding="utf-8",
    )
    assert core.check_include_directive(cfg) is True


# --- T7 — absent/commented/missing → False
def test_check_include_directive_returns_false_when_absent(tmp_path):
    # (a) absent
    cfg = _main_ssh(tmp_path)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("Host github.com\n  HostName github.com\n", encoding="utf-8")
    assert core.check_include_directive(cfg) is False
    # (b) commented out
    cfg.write_text("# Include config.d/*\n", encoding="utf-8")
    assert core.check_include_directive(cfg) is False
    # (c) main config missing
    missing = tmp_path / "no-such-config"
    assert core.check_include_directive(missing) is False


@pytest.fixture
def wizard_entry_ok(monkeypatch, tmp_path):
    """Stub the wizard's entry-check so tests don't depend on the operator's
    real ~/.ssh contents. Creates 3 zero-byte placeholder files in tmp_path."""
    auto_priv = tmp_path / "ansispire_ed25519"
    auto_pub = tmp_path / "ansispire_ed25519.pub"
    pers_pub = tmp_path / "id_ed25519.pub"
    for p in (auto_priv, auto_pub, pers_pub):
        p.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(core, "DEFAULT_AUTOMATION_PRIVATE_KEY", auto_priv)
    monkeypatch.setattr(core, "DEFAULT_AUTOMATION_PUBLIC_KEY", auto_pub)
    monkeypatch.setattr(core, "DEFAULT_PERSONAL_PUBLIC_KEY", pers_pub)


# --- T8 (R11) — wizard collects expanded field set with defaults; key branch ----
def test_prompt_new_host_collects_full_fields_key_branch(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    pem = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAA\n"
        "-----END OPENSSH PRIVATE KEY-----"
    )
    # order: alias / ip / bootstrap_user (default) / auth (default p→use 'k') /
    #        PEM line 1 / line 2 / line 3 / bootstrap_port (default) /
    #        managed_user (default) / managed_port (default)
    inputs = iter([
        "test-wiz", "192.0.2.99", "",
        "k",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "b3BlbnNzaC1rZXktdjEAAAAA",
        "-----END OPENSSH PRIVATE KEY-----",
        "", "", "",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    result = core.prompt_new_host("dev")
    assert result["alias"] == "test-wiz"
    assert result["ip"] == "192.0.2.99"
    assert result["user"] == "root"
    assert result["port"] == 22
    assert result["managed_user"] == "ansible"
    assert result["managed_port"] == 1156
    assert result["auth_method"] == "k"
    assert result["ssh_password"] is None
    assert result["sudo_password"] is None  # bootstrap user = root → skipped
    assert "-----BEGIN" in result["private_key_text"]
    assert "-----END" in result["private_key_text"]


# --- T8b (R11) — password branch with non-root user (sudo password collected) ----
def test_prompt_new_host_password_branch_nonroot_collects_sudo(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    inputs = iter([
        "test-pw", "192.0.2.40",
        "ubuntu",       # non-root bootstrap user
        "p",            # password branch
        "", "", "",     # port (default 22), managed_user (default), managed_port (default)
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    pw_iter = iter(["ssh-secret", ""])  # SSH pw, sudo pw (blank → reuse SSH)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(pw_iter))
    result = core.prompt_new_host("dev")
    assert result["auth_method"] == "p"
    assert result["ssh_password"] == "ssh-secret"
    assert result["sudo_password"] == "ssh-secret"  # blank → fallback to SSH pw
    assert result["user"] == "ubuntu"
    assert result["private_key_text"] is None


# --- T9 (R11) — managed_port validation: 22 rejected → reprompt → accept 1156 ----
def test_prompt_new_host_validation_retry_on_bad_managed_port(
    fake_inventory, wizard_entry_ok, monkeypatch, capsys
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    inputs = iter([
        "test-wiz", "192.0.2.99", "",
        "k",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "abc",
        "-----END OPENSSH PRIVATE KEY-----",
        "",        # bootstrap port (default 22)
        "",        # managed_user (default ansible)
        "22",      # managed_port: bad
        "1156",    # managed_port: ok
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    result = core.prompt_new_host("dev")
    assert result["managed_port"] == 1156
    out = capsys.readouterr().out
    assert "managed_port=22 not allowed" in out


# --- T10 — KeyboardInterrupt → graceful None
def test_prompt_new_host_keyboard_interrupt_returns_none(
    fake_inventory, wizard_entry_ok, monkeypatch
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())

    def boom(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", boom)
    assert core.prompt_new_host("dev") is None


# --- T10b (R11) — entry-check rejection when standard keys are missing ----
def test_prompt_new_host_entry_check_missing_keys(
    fake_inventory, monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(core, "DEFAULT_AUTOMATION_PRIVATE_KEY", tmp_path / "no-such")
    monkeypatch.setattr(core, "DEFAULT_AUTOMATION_PUBLIC_KEY", tmp_path / "no-such.pub")
    monkeypatch.setattr(core, "DEFAULT_PERSONAL_PUBLIC_KEY", tmp_path / "no-id.pub")
    result = core.prompt_new_host("dev")
    assert result is None
    err = capsys.readouterr().err
    assert "prerequisite missing" in err
    assert "ssh-keygen" in err


# --- T11 (R11/T2) — add-host CLI wizard mode (key branch): full lifecycle ----
def test_add_host_cli_wizard_mode_key_branch_full_lifecycle(
    fake_inventory, wizard_entry_ok, monkeypatch, capsys, tmp_path
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    inputs = iter([
        "test-wiz", "192.0.2.99", "",
        "k",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "abc",
        "-----END OPENSSH PRIVATE KEY-----",
        "", "", "",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    # Mock both onboard + verify as successful so cleanup runs
    def fake_run(**kwargs):
        return core.RunSummary(
            run_id=f"vps-runner-mock-dev-{kwargs.get('action', 'onboard')}",
            action=kwargs.get("action", "onboard"),
            env="dev",
            status="successful",
            rc=0,
            artifact_dir="/tmp/none",
            hosts=[],
        )

    monkeypatch.setattr(core, "run_playbook", fake_run)

    rc = cli.main(["add-host", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wrote temp bootstrap key" in out
    assert "cleaned up temp key" in out
    # inventory persisted; bootstrap_key cleared to null on success
    data = yaml.safe_load(core.host_vars_path("dev", "test-wiz").read_text())
    assert data["ansible_host"] == "192.0.2.99"
    assert data["vps_runner"]["bootstrap_user"] == "root"
    assert data["vps_runner"]["bootstrap_port"] == 22
    # bootstrap_key field may exist as None (cleared) or be absent — both OK
    assert data["vps_runner"].get("bootstrap_key") in (None, )
    # temp key file cleaned up
    assert not (tmp_path / "tempkeys" / "test-wiz.key").exists()


# --- T11b (R11/T2) — key branch onboard failure path retains temp key + bootstrap_key ----
def test_add_host_cli_wizard_mode_key_branch_onboard_failure_retains_key(
    fake_inventory, wizard_entry_ok, monkeypatch, capsys, tmp_path
):
    monkeypatch.setattr(core.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(cli.sys, "stdin", _FakeStdin())
    monkeypatch.setattr(core, "TEMP_KEY_DIR", tmp_path / "tempkeys")
    inputs = iter([
        "fail-wiz", "192.0.2.50", "",
        "k",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "abc",
        "-----END OPENSSH PRIVATE KEY-----",
        "", "", "",
    ])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    def fake_run_fail(**kwargs):
        return core.RunSummary(
            run_id="vps-runner-mock-dev-onboard",
            action="onboard", env="dev", status="failed", rc=4,
            artifact_dir="/tmp/none", hosts=[],
        )

    monkeypatch.setattr(core, "run_playbook", fake_run_fail)

    rc = cli.main(["add-host", "--env", "dev"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "onboard 失败" in out
    # temp key kept for retry
    assert (tmp_path / "tempkeys" / "fail-wiz.key").exists()
    # bootstrap_key persisted into host_vars for retry hint
    data = yaml.safe_load(core.host_vars_path("dev", "fail-wiz").read_text())
    assert data["vps_runner"]["bootstrap_key"].endswith("fail-wiz.key")


# --- T12 — flag mode preserves R6 inventory-only contract (R11 only changes hint text)
def test_add_host_cli_flag_mode_unchanged_from_r6(fake_inventory, capsys):
    rc = cli.main([
        "add-host", "delta-r6",
        "--ip", "192.0.2.50",
        "--env", "dev",
        "--port", "2222",
        "--user", "deploy",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    # R11 changed the post-add hint; inventory contract unchanged
    assert "onboard delta-r6 --env dev --first-time" in out
    data = yaml.safe_load(core.host_vars_path("dev", "delta-r6").read_text())
    assert data["ansible_port"] == 2222


# --- T13 — onboard writes SSH config on success (operator key)
def test_onboard_cli_writes_ssh_config_on_success(fake_inventory, tmp_path, monkeypatch, capsys):
    ssh_d = _ssh_dir(tmp_path)
    monkeypatch.setattr(core, "DEFAULT_SSH_CONFIG_DIR", ssh_d)
    # Make Include directive check pass cheaply by pointing at a tmp file with the line.
    main_cfg = _main_ssh(tmp_path)
    main_cfg.parent.mkdir(parents=True, exist_ok=True)
    main_cfg.write_text("Include config.d/*\n", encoding="utf-8")
    monkeypatch.setattr(core, "DEFAULT_SSH_MAIN_CONFIG", main_cfg)

    def fake_run(**kwargs):
        return core.RunSummary(
            run_id="vps-runner-20260522T000000Z-dev-onboard",
            action="onboard", env="dev", status="successful", rc=0,
            artifact_dir="/tmp/none", hosts=[],
        )

    with patch.object(core, "run_playbook", side_effect=fake_run):
        rc = cli.main(["onboard", "alpha", "--env", "dev"])
    assert rc == 0
    target = ssh_d / "alpha.conf"
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "Host alpha" in text
    assert "HostName 192.0.2.1" in text  # from fake_inventory
    assert "id_ed25519" in text
    assert "ansispire_ed25519" not in text
    out = capsys.readouterr().out
    assert "wrote local SSH alias" in out


# --- T14 — onboard does NOT write SSH config on failure
def test_onboard_cli_does_not_write_ssh_config_on_failure(
    fake_inventory, tmp_path, monkeypatch
):
    ssh_d = _ssh_dir(tmp_path)
    monkeypatch.setattr(core, "DEFAULT_SSH_CONFIG_DIR", ssh_d)

    def fake_run(**kwargs):
        return core.RunSummary(
            run_id="vps-runner-20260522T000000Z-dev-onboard",
            action="onboard", env="dev", status="failed", rc=2,
            artifact_dir="/tmp/none", hosts=[],
        )

    with patch.object(core, "run_playbook", side_effect=fake_run):
        rc = cli.main(["onboard", "alpha", "--env", "dev"])
    assert rc == 1
    assert not (ssh_d / "alpha.conf").exists()


# --- T15 — remove deletes SSH config regardless of cleanup_remote
def test_remove_cli_deletes_ssh_config_regardless_of_cleanup_remote(
    fake_inventory, tmp_path, monkeypatch, capsys
):
    ssh_d = _ssh_dir(tmp_path)
    monkeypatch.setattr(core, "DEFAULT_SSH_CONFIG_DIR", ssh_d)
    # Seed an SSH alias file we expect to be deleted alongside alpha's inventory.
    core.write_ssh_config(
        "alpha", hostname="192.0.2.1", port=1156, user="deploy",
        ssh_config_dir=ssh_d,
    )
    assert (ssh_d / "alpha.conf").exists()

    rc = cli.main(["remove", "alpha", "--env", "dev", "--yes"])
    assert rc == 0
    assert not (ssh_d / "alpha.conf").exists()
    out = capsys.readouterr().out
    assert "removed ~/.ssh/config.d/alpha.conf" in out


# ---------------------------------------------------------------------------
# Integration tests (unchanged from R6 — real ansible-runner against
# unreachable docs-only IPs).
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_envvars_artifact_excludes_unwhitelisted(tmp_path, monkeypatch):
    """Reproduces codex review P1.3: the runner's `command` artifact records
    the envvars dict; without an allowlist, ambient secrets (e.g. fake token
    we inject below) would land in the artifact. With the allowlist, only
    PATH / ANSIBLE_* / locale vars are recorded."""
    env_dir = tmp_path / "inventory" / "vps_runner" / "dev"
    (env_dir / "host_vars").mkdir(parents=True)
    (env_dir / "hosts.yml").write_text(
        "---\nall:\n  children:\n    vps_targets:\n      hosts:\n        unreachable-1:\n",
        encoding="utf-8",
    )
    (env_dir / "host_vars" / "unreachable-1.yml").write_text(
        "---\nansible_host: 192.0.2.99\nansible_port: 22\nansible_user: nobody\n"
        "ansible_python_interpreter: /usr/bin/python3\n"
        "ansible_ssh_common_args: '-o ConnectTimeout=3 -o BatchMode=yes'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(core, "INVENTORY_ROOT", tmp_path / "inventory" / "vps_runner")
    monkeypatch.setattr(core, "ARTIFACT_ROOT", tmp_path / "artifacts")
    monkeypatch.setenv("FAKE_LEAKED_TOKEN_DO_NOT_USE", "sk_leak_canary_value_12345")

    summary = core.run_playbook(
        action="audit", env="dev", playbook="audit.yml",
        limit="unreachable-1", quiet=True,
    )
    command_file = Path(summary.artifact_dir) / "command"
    assert command_file.exists()
    command_text = command_file.read_text(encoding="utf-8")
    assert "FAKE_LEAKED_TOKEN_DO_NOT_USE" not in command_text, (
        "unwhitelisted env var leaked into artifact command file"
    )
    assert "sk_leak_canary_value_12345" not in command_text, (
        "leaked value found in artifact — envvars whitelist is broken"
    )
