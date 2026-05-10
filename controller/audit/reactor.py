#!/usr/bin/env python3
"""Advanced EDA Reactor v2.3 — Observability & Robustness.

Supports '_contains' matching, dynamic resolution, and verbose diagnostic logging.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

# Configuration
JSONL_PATH = os.environ.get("JSONL_PATH", "/var/log/semaphore/events.jsonl")
RULES_PATH = os.environ.get("RULES_PATH", "/etc/ansispire/eda/rules.json")
SCHEMA_PATH = os.environ.get("EVENTS_SCHEMA_PATH", "/etc/ansispire/eda/events.schema.json")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
WEBHOOK_URL = os.environ.get("EDA_WEBHOOK_URL", "")

# Semaphore API Config
SEMAPHORE_URL = os.environ.get("SEMAPHORE_URL", "http://semaphore:3000")
SEMAPHORE_TOKEN = os.environ.get("SEMAPHORE_API_TOKEN", "")

LAST_TRIGGERED = {}
TEMPLATE_CACHE = {}

def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [reactor] {msg}", file=sys.stderr, flush=True)

def load_rules() -> list:
    try:
        if not os.path.exists(RULES_PATH):
            log(f"rules file missing: {RULES_PATH}")
            return []
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            rules = data.get("rules", [])
            return rules
    except Exception as e:
        log(f"error loading rules: {e}")
        return []

def schema_banner() -> str:
    """Read events.schema.json once at startup and return a one-line tag for
    the log. Best-effort — never raises."""
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            s = json.load(f)
        return f"{s.get('$id', SCHEMA_PATH)}@{s.get('version', '?')}"
    except Exception:
        return "unavailable"

def match_rule(event_payload: dict, rule: dict) -> bool:
    if not rule.get("enabled", True):
        return False
    condition = rule.get("condition", {})
    payload_wrapper = event_payload.get("payload", {})
    event = payload_wrapper.get("event", {})

    if not event:
        return False

    for key, value in condition.items():
        if key.endswith("_contains"):
            real_key = key.replace("_contains", "")
            actual_val = str(event.get(real_key, ""))
            if value not in actual_val:
                return False
        elif event.get(key) != value:
            return False
            
    rule_name = rule.get("name", "unnamed")
    cooldown = rule.get("cooldown", 60)
    now = time.time()
    if rule_name in LAST_TRIGGERED and (now - LAST_TRIGGERED[rule_name]) < cooldown:
        log(f"skipping {rule_name}: in cooldown ({(now - LAST_TRIGGERED[rule_name]):.1f}s < {cooldown}s)")
        return False
            
    return True

def get_project_id_by_name(project_name: str) -> int:
    url = f"{SEMAPHORE_URL}/api/projects"
    headers = {"Authorization": f"Bearer {SEMAPHORE_TOKEN}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            projects = json.loads(resp.read())
            for p in projects:
                if p.get("name") == project_name:
                    return p.get("id")
    except Exception as e:
        log(f"project lookup failed for {project_name}: {e}")
    return None

def get_template_id_by_name(project_id: int, template_name: str) -> int:
    cache_key = f"{project_id}:{template_name}"
    if cache_key in TEMPLATE_CACHE:
        return TEMPLATE_CACHE[cache_key]

    url = f"{SEMAPHORE_URL}/api/project/{project_id}/templates"
    headers = {"Authorization": f"Bearer {SEMAPHORE_TOKEN}"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            templates = json.loads(resp.read())
            for t in templates:
                if t.get("name") == template_name:
                    tid = t.get("id")
                    TEMPLATE_CACHE[cache_key] = tid
                    return tid
    except Exception as e:
        log(f"template lookup failed for {template_name}: {e}")
    return None

def trigger_semaphore_task(action: dict) -> None:
    template_id = action.get("template_id")
    template_name = action.get("template_name")
    project_id = action.get("project_id")
    project_name = action.get("project_name", "ansispire")
    
    if not project_id and project_name:
        project_id = get_project_id_by_name(project_name)
    
    if not project_id:
        log(f"remediation failed: could not resolve project {project_name}")
        return

    if not template_id and template_name:
        template_id = get_template_id_by_name(project_id, template_name)

    if not template_id:
        log(f"remediation failed: could not resolve template {template_name} in project {project_id}")
        return

    url = f"{SEMAPHORE_URL}/api/project/{project_id}/tasks"
    if not SEMAPHORE_TOKEN:
        log("remediation failed: SEMAPHORE_API_TOKEN not set")
        return

    payload = json.dumps({"template_id": int(template_id)}).encode()
    
    try:
        req = urllib.request.Request(
            url, 
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SEMAPHORE_TOKEN}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            log(f"remediation triggered: template={template_id} ({template_name or 'ID'}), status={resp.status}")
    except Exception as e:
        log(f"remediation failed (Template {template_id}): {e}")

def process_event(event_line: str, rules: list) -> None:
    line = event_line.strip()
    if not line: return

    try:
        payload = json.loads(line)
        # Minimalist event logging for observability
        event_type = payload.get("payload", {}).get("event", {}).get("type", "unknown")
        log(f"received event: {event_type}")
    except json.JSONDecodeError as e:
        log(f"JSON parse error: {e}. Line starts with: {line[:50]}...")
        return
    except Exception as e:
        log(f"Unexpected processing error: {e}")
        return

    for rule in rules:
        if match_rule(payload, rule):
            log(f"MATCH FOUND: {rule.get('name')}")
            LAST_TRIGGERED[rule.get("name")] = time.time()
            for action in rule.get("actions", []):
                if action.get("type") == "semaphore_api":
                    trigger_semaphore_task(action)
                elif action.get("type") == "webhook":
                    # Webhook logic skipped for brevity in log, implement as needed
                    pass

def main() -> None:
    log(f"starting advanced reactor v2.3, monitoring {JSONL_PATH}")
    log(f"event schema: {schema_banner()}")
    if not os.path.exists(JSONL_PATH):
        log(f"warning: {JSONL_PATH} does not exist yet. waiting...")

    rules = load_rules()
    log(f"loaded {len(rules)} rules")
    
    try:
        with open(JSONL_PATH, "r") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(POLL_INTERVAL)
                    # Rules hot-reload is useful but maybe too frequent? 
                    # For now keep it as per requirement.
                    rules = load_rules()
                    continue
                process_event(line, rules)
    except Exception as e:
        log(f"fatal error: {e}")
        time.sleep(5)
        main()

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass
