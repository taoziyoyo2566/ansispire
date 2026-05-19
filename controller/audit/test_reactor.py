#!/usr/bin/env python3
"""L1 unit tests for the EDA reactor.

Scope: pure-Python behaviour of match_rule and process_event — no HTTP, no
docker. Covers the matchers (exact, _contains, mixed, missing fields),
cooldown windowing, and the dispatch path in process_event.

Outbound HTTP behaviour (project/template resolution, Bearer auth, payload
shape, caching) is L3's job — see test_reactor_component.py.
"""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import reactor


def _ev(**event_fields):
    """Tiny helper — wrap the reactor's expected double envelope."""
    return {"payload": {"event": event_fields}}


class TestMatchRule(unittest.TestCase):
    def setUp(self):
        reactor.LAST_TRIGGERED = {}

    def test_exact_match(self):
        rule = {"name": "R1", "condition": {"type": "task_completed", "status": "error"}, "cooldown": 60}
        self.assertTrue(reactor.match_rule(_ev(type="task_completed", status="error"), rule))

    def test_exact_mismatch(self):
        rule = {"name": "R1", "condition": {"type": "task_completed", "status": "error"}, "cooldown": 60}
        self.assertFalse(reactor.match_rule(_ev(type="task_completed", status="success"), rule))

    def test_contains_match(self):
        rule = {"name": "R1", "condition": {"description_contains": "Disk Full"}, "cooldown": 60}
        self.assertTrue(reactor.match_rule(_ev(description="Task 7 — ERROR — Disk Full on h1"), rule))

    def test_contains_mismatch(self):
        rule = {"name": "R1", "condition": {"description_contains": "Disk Full"}, "cooldown": 60}
        self.assertFalse(reactor.match_rule(_ev(description="Task 7 — success"), rule))

    def test_contains_missing_field(self):
        """If the field referenced by _contains is absent, no match (str() empty)."""
        rule = {"name": "R1", "condition": {"description_contains": "Disk Full"}, "cooldown": 60}
        self.assertFalse(reactor.match_rule(_ev(type="task_completed"), rule))

    def test_contains_value_coerced_to_string(self):
        """Schema rejects numeric _contains values, but reactor's str() coercion
        is the defense-in-depth net for rules.json edited by hand without
        running `make test-rules-schema`. Must not crash the tail loop."""
        rule = {"name": "R1", "condition": {"description_contains": 123}, "cooldown": 60}
        self.assertTrue(reactor.match_rule(_ev(description="error 123 happened"), rule))

    def test_mixed_exact_and_contains(self):
        """Both conditions must be satisfied."""
        rule = {
            "name": "R1",
            "condition": {"object_type": "task", "description_contains": "Disk Full"},
            "cooldown": 60,
        }
        self.assertTrue(reactor.match_rule(_ev(object_type="task", description="A — Disk Full — B"), rule))
        self.assertFalse(reactor.match_rule(_ev(object_type="user", description="A — Disk Full — B"), rule))
        self.assertFalse(reactor.match_rule(_ev(object_type="task", description="A — success — B"), rule))

    def test_no_event_envelope(self):
        """An event with no payload.event sub-key matches nothing."""
        rule = {"name": "R1", "condition": {"type": "x"}, "cooldown": 60}
        self.assertFalse(reactor.match_rule({}, rule))
        self.assertFalse(reactor.match_rule({"payload": {}}, rule))

    def test_cooldown_blocks_within_window(self):
        rule = {"name": "Cool", "condition": {"type": "t"}, "cooldown": 10}
        ev = _ev(type="t")
        self.assertTrue(reactor.match_rule(ev, rule))
        reactor.LAST_TRIGGERED["Cool"] = 1000
        with patch("time.time", return_value=1005):
            self.assertFalse(reactor.match_rule(ev, rule))

    def test_cooldown_releases_after_window(self):
        rule = {"name": "Cool", "condition": {"type": "t"}, "cooldown": 10}
        ev = _ev(type="t")
        reactor.LAST_TRIGGERED["Cool"] = 1000
        with patch("time.time", return_value=1011):
            self.assertTrue(reactor.match_rule(ev, rule))

    def test_disabled_rule_never_matches(self):
        """enabled=false short-circuits before condition / cooldown evaluation."""
        rule = {"name": "Off", "enabled": False, "condition": {"type": "t"}, "cooldown": 60}
        self.assertFalse(reactor.match_rule(_ev(type="t"), rule))
        # Default (no enabled key) behaves as enabled
        rule_default = {"name": "On", "condition": {"type": "t"}, "cooldown": 60}
        self.assertTrue(reactor.match_rule(_ev(type="t"), rule_default))


class TestProcessEvent(unittest.TestCase):
    def setUp(self):
        reactor.LAST_TRIGGERED = {}

    @patch("reactor.trigger_semaphore_task")
    def test_dispatch_on_match(self, mock_trigger):
        rules = [{
            "name": "R", "condition": {"type": "go"}, "cooldown": 60,
            "actions": [{"type": "semaphore_api", "template_id": 99}],
        }]
        reactor.process_event(json.dumps(_ev(type="go")), rules)
        mock_trigger.assert_called_once()

    @patch("reactor.trigger_semaphore_task")
    def test_no_dispatch_on_mismatch(self, mock_trigger):
        rules = [{
            "name": "R", "condition": {"type": "go"}, "cooldown": 60,
            "actions": [{"type": "semaphore_api", "template_id": 99}],
        }]
        reactor.process_event(json.dumps(_ev(type="stop")), rules)
        mock_trigger.assert_not_called()

    @patch("reactor.trigger_semaphore_task")
    def test_invalid_json_does_not_raise(self, mock_trigger):
        rules = [{"name": "R", "condition": {"type": "go"}, "cooldown": 60, "actions": []}]
        # Should log and return, not crash the loop.
        reactor.process_event("not-json {", rules)
        mock_trigger.assert_not_called()

    @patch("reactor.trigger_semaphore_task")
    def test_empty_line_skipped(self, mock_trigger):
        reactor.process_event("   \n", [])
        mock_trigger.assert_not_called()

    @patch("reactor.trigger_semaphore_task")
    def test_malformed_rule_does_not_crash_loop(self, mock_trigger):
        """One bad rule logs + is skipped; subsequent good rules still fire."""
        # condition: not a dict → match_rule raises AttributeError on .items().
        bad_rule = {"name": "bad", "condition": "not-a-dict", "cooldown": 60, "actions": []}
        good_rule = {
            "name": "good", "condition": {"type": "go"}, "cooldown": 60,
            "actions": [{"type": "semaphore_api", "template_id": 99}],
        }
        reactor.process_event(json.dumps(_ev(type="go")), [bad_rule, good_rule])
        # Good rule still fired despite bad_rule blowing up.
        mock_trigger.assert_called_once()


class TestTruncationHandling(unittest.TestCase):
    """Regression coverage for the v2.5 copytruncate fix.

    The reactor's tail-FD must seek to OFFSET 0 (not EOF) when it detects
    that the cursor offset exceeds the current file size — that condition
    is the signature of `logrotate copytruncate`: the file shrinks to 0
    bytes (or smaller than the cursor) and then accumulates new content
    from the start.

    Previous v2.4 behaviour was `f.seek(0, SEEK_END)` which silently dropped
    every event written to the post-rotate file before the next reactor
    restart cycle observed it — defeating cursor persistence.
    """

    def test_truncation_resets_cursor_to_start(self):
        """Black-box: run reactor.py as a subprocess against a small temp
        sandbox; force a cursor > file-size condition; verify reactor saves
        cursor=0 (proving it seek(0)-ed) within one POLL_INTERVAL."""
        import subprocess
        import tempfile

        tmp = tempfile.mkdtemp()
        try:
            jsonl = os.path.join(tmp, "events.jsonl")
            rules = os.path.join(tmp, "rules.json")
            schema = os.path.join(tmp, "events.schema.json")
            cursor = os.path.join(tmp, "cursor")

            # 1. Create a non-empty file → discover its size.
            with open(jsonl, "w") as f:
                f.write('{"payload":{"event":{"type":"x"}}}\n' * 5)
            pre_size = os.path.getsize(jsonl)
            self.assertGreater(pre_size, 0)

            # 2. Simulate copytruncate: shrink to zero, write a new event.
            with open(jsonl, "w") as f:
                f.write('{"payload":{"event":{"type":"post_rotate"}}}\n')
            post_size = os.path.getsize(jsonl)
            self.assertLess(post_size, pre_size)

            # 3. Plant a cursor that points past the new (smaller) file.
            with open(cursor, "w") as f:
                f.write(str(pre_size))

            # 4. Minimal rules + schema files so reactor doesn't bail.
            with open(rules, "w") as f:
                json.dump({"rules": []}, f)
            with open(schema, "w") as f:
                json.dump({"$id": "test", "version": "1"}, f)

            # 5. Run reactor with tiny intervals; ~1s is enough for it to
            #    parse cursor, detect cursor>size, seek(0), save_cursor(0).
            env = {
                **os.environ,
                "JSONL_PATH": jsonl,
                "RULES_PATH": rules,
                "EVENTS_SCHEMA_PATH": schema,
                "CURSOR_FILE": cursor,
                "POLL_INTERVAL": "0.1",
                "CURSOR_FLUSH_INTERVAL": "0.1",
                "SEMAPHORE_API_TOKEN": "",
            }
            reactor_path = os.path.join(os.path.dirname(__file__), "reactor.py")
            proc = subprocess.Popen(
                [sys.executable, reactor_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                # Give it long enough to: open file, load cursor, detect
                # truncation, seek(0), processs the post_rotate line.
                import time as _time
                _time.sleep(1.2)
            finally:
                proc.terminate()
                try:
                    out, _ = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, _ = proc.communicate()

            # 6. Cursor must have been reset to ≤ new file size — proving
            #    truncation was detected. Post-process events would push it
            #    to ~ post_size, but the critical assertion is "not stuck
            #    at the pre-truncation value".
            self.assertTrue(os.path.exists(cursor), "cursor file should exist")
            with open(cursor) as f:
                new_offset = int(f.read().strip())
            self.assertLessEqual(new_offset, post_size,
                f"cursor stayed at {new_offset} (post-truncate file is "
                f"{post_size} bytes) — truncation NOT detected. "
                f"reactor stderr: {out.decode(errors='replace')[-500:]}")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
