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


if __name__ == "__main__":
    unittest.main()
