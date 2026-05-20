#!/usr/bin/env python3
"""L2 contract test — rules.json ↔ bootstrap.yml.

Catches the failure mode that bit us in round 0: rules.json references a
template_name that bootstrap.yml does not register, so the rule fires at
runtime and reactor logs "could not resolve template" — silently. This
test fails at PR time on that drift.

Stdlib + PyYAML. No HTTP, no docker. See docs/test-specs/eda-rules-contract.md.
"""

import json
import os
import sys
import unittest

from jsonschema import Draft7Validator
import yaml  # PyYAML — comes via the project .venv (ansible dependency)

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
RULES_PATH = os.path.join(REPO_ROOT, "extensions", "eda", "rules.json")
SCHEMA_PATH = os.path.join(REPO_ROOT, "extensions", "eda", "events.schema.json")
RULES_SCHEMA_PATH = os.path.join(REPO_ROOT, "extensions", "eda", "rules.schema.json")
BOOTSTRAP_PATH = os.path.join(REPO_ROOT, "controller", "semaphore", "bootstrap.yml")
REGISTER_TASK_NAME = "Register remediation templates (idempotent)"


def _load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_bootstrap_templates():
    """Return the list of template names declared in bootstrap.yml's
    `Register remediation templates` task. Empty list if the task is
    missing — caller asserts on emptiness."""
    with open(BOOTSTRAP_PATH, "r", encoding="utf-8") as f:
        plays = yaml.safe_load(f)
    for play in plays:
        for task in play.get("tasks", []) or []:
            if task.get("name") == REGISTER_TASK_NAME:
                return [item["name"] for item in task.get("loop", [])]
    return []


class TestRulesJsonStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _load_rules()

    def test_C1_rules_is_valid_json_dict(self):
        self.assertIsInstance(self.doc, dict)
        self.assertIn("rules", self.doc)
        self.assertIsInstance(self.doc["rules"], list)
        self.assertGreater(len(self.doc["rules"]), 0)

    def test_C2_each_rule_has_required_keys(self):
        for r in self.doc["rules"]:
            with self.subTest(rule=r.get("name", "<unnamed>")):
                self.assertIn("name", r)
                self.assertIn("condition", r)
                self.assertIn("actions", r)
                self.assertIsInstance(r["actions"], list)

    def test_C3_rule_names_unique(self):
        names = [r["name"] for r in self.doc["rules"]]
        self.assertEqual(len(names), len(set(names)),
                         f"duplicate rule names: {[n for n in names if names.count(n) > 1]}")

    def test_C4_semaphore_api_actions_have_required_fields(self):
        for r in self.doc["rules"]:
            for i, a in enumerate(r["actions"]):
                if a.get("type") != "semaphore_api":
                    continue
                with self.subTest(rule=r["name"], action_idx=i):
                    self.assertIn("template_name", a)
                    self.assertIn("project_name", a)
                    self.assertTrue(a["template_name"], "template_name must be non-empty")
                    self.assertTrue(a["project_name"], "project_name must be non-empty")

    def test_C10_rules_schema_rejects_numeric_contains_values(self):
        """Schema must reject _contains values that aren't strings —
        substring match against a number is semantically meaningless."""
        with open(RULES_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        bad_doc = {
            "rules": [{
                "name": "bad contains",
                "condition": {"description_contains": 123},
                "actions": [{"type": "webhook", "url": "http://example.invalid"}],
            }],
        }
        errors = list(Draft7Validator(schema).iter_errors(bad_doc))
        self.assertGreater(len(errors), 0,
                           "numeric _contains values must be rejected by the schema")

    def test_C11_rules_schema_requires_template_for_semaphore_api(self):
        """reactor.py:trigger_semaphore_task POSTs to
        /api/project/{id}/tasks with a template_id payload — neither the
        project nor the template is optional, even though the action
        type itself only mandates the project identifier."""
        with open(RULES_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        bad_doc = {
            "rules": [{
                "name": "bad semaphore action",
                "condition": {"object_type": "task"},
                "actions": [{"type": "semaphore_api", "project_name": "ansispire"}],
            }],
        }
        errors = list(Draft7Validator(schema).iter_errors(bad_doc))
        self.assertGreater(len(errors), 0,
                           "semaphore_api actions must identify a template (id or name)")


class TestBootstrapTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BOOTSTRAP_PATH, "r", encoding="utf-8") as f:
            cls.plays = yaml.safe_load(f)
        cls.tpl_names = _load_bootstrap_templates()

    def test_C5_bootstrap_is_valid_yaml(self):
        self.assertIsInstance(self.plays, list)
        self.assertGreater(len(self.plays), 0)

    def test_C6_register_task_exists(self):
        self.assertGreater(
            len(self.tpl_names), 0,
            f"bootstrap.yml is missing the '{REGISTER_TASK_NAME}' task — "
            "remediation templates would never be registered",
        )

    def test_C8_bootstrap_template_names_unique(self):
        self.assertEqual(
            len(self.tpl_names), len(set(self.tpl_names)),
            f"duplicate template names in bootstrap loop: {self.tpl_names}",
        )


class TestContractAlignment(unittest.TestCase):
    """Cross-file invariants — rules ↔ bootstrap, rules ↔ schema."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _load_rules()
        cls.bootstrap_names = set(_load_bootstrap_templates())
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

    def test_C7_every_rule_template_is_registered_in_bootstrap(self):
        missing = []
        for r in self.doc["rules"]:
            for a in r["actions"]:
                if a.get("type") != "semaphore_api":
                    continue
                tpl = a.get("template_name")
                if tpl and tpl not in self.bootstrap_names:
                    missing.append((r["name"], tpl))
        self.assertEqual(
            missing, [],
            f"rules.json references template_name(s) that bootstrap.yml does NOT register: "
            f"{missing}. Bootstrap registers: {sorted(self.bootstrap_names)}",
        )

    def test_C9_rule_condition_keys_are_in_event_schema(self):
        """Every condition key (after stripping _contains) must be a known
        property of payload.event in events.schema.json. Catches the case
        where rules.json starts matching on a field the schema does not
        document — schema and rules must evolve together."""
        event_props = set(
            self.schema.get("properties", {})
            .get("payload", {})
            .get("properties", {})
            .get("event", {})
            .get("properties", {})
            .keys()
        )
        self.assertGreater(len(event_props), 0,
                           "events.schema.json missing payload.event.properties")

        unknown = []
        for r in self.doc["rules"]:
            for raw_key in r.get("condition", {}).keys():
                key = raw_key[: -len("_contains")] if raw_key.endswith("_contains") else raw_key
                if key not in event_props:
                    unknown.append((r["name"], raw_key))
        self.assertEqual(
            unknown, [],
            f"rules.json references condition key(s) not declared in events.schema.json: "
            f"{unknown}. Schema knows: {sorted(event_props)}",
        )


if __name__ == "__main__":
    unittest.main()
