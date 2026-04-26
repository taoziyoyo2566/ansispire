#!/usr/bin/env python3
"""Lightweight EDA Reactor — Processes Audit Events and Triggers Actions.

Tails the JSONL audit sink and evaluates events against rules defined in
extensions/eda/rules.json. Supports Webhook notifications and local command
execution (e.g., self-healing playbooks).
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
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
WEBHOOK_URL = os.environ.get("EDA_WEBHOOK_URL", "")

def log(msg: str) -> None:
    print(f"[reactor] {msg}", file=sys.stderr, flush=True)

def load_rules() -> list:
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("rules", [])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"warning: could not load rules from {RULES_PATH}: {e}")
        return []

def match_rule(event_payload: dict, rule: dict) -> bool:
    """Simple attribute matcher. Returns True if all rule conditions match."""
    condition = rule.get("condition", {})
    event = event_payload.get("event", {})
    
    for key, value in condition.items():
        # Handle nested keys like 'event.type'
        if event.get(key) != value:
            return False
    return True

def trigger_webhook(action: dict, event_payload: dict) -> None:
    url = action.get("url", WEBHOOK_URL)
    if not url:
        log("skipping webhook: no URL configured")
        return
    
    payload = {
        "title": f"EDA Alert: {action.get('name', 'Action Triggered')}",
        "event": event_payload,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        log(f"webhook delivered to {url}")
    except Exception as e:
        log(f"webhook failure: {e}")

def trigger_shell(action: dict, event_payload: dict) -> None:
    command = action.get("command")
    if not command:
        return
    
    # Security: In a production system, we should use a template/whitelist approach.
    # For this POC, we allow limited commands defined in the rules file.
    log(f"executing reactive command: {command}")
    try:
        # Pass event data as environment variable to the subprocess
        env = os.environ.copy()
        env["EDA_EVENT_JSON"] = json.dumps(event_payload)
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        if result.returncode == 0:
            log("command executed successfully")
        else:
            log(f"command failed (rc={result.returncode}): {result.stderr}")
    except Exception as e:
        log(f"shell execution error: {e}")

def process_event(event_line: str, rules: list) -> None:
    try:
        payload = json.loads(event_line)
        # log(f"debug: processing event type={payload.get('event', {}).get('type')}")
    except json.JSONDecodeError:
        return

    for rule in rules:
        if match_rule(payload, rule):
            log(f"rule matched: {rule.get('name', 'unnamed')}")
            for action in rule.get("actions", []):
                action_type = action.get("type")
                if action_type == "webhook":
                    trigger_webhook(action, payload)
                elif action_type == "shell":
                    trigger_shell(action, payload)

def main() -> None:
    log(f"starting reactor, monitoring {JSONL_PATH}")
    rules = load_rules()
    log(f"loaded {len(rules)} rules from {RULES_PATH}")

    # Tail the file
    try:
        with open(JSONL_PATH, "r") as f:
            # Go to the end of file to start monitoring new events
            f.seek(0, os.SEEK_END)
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(POLL_INTERVAL)
                    continue
                
                process_event(line, rules)
    except FileNotFoundError:
        log(f"error: {JSONL_PATH} not found. Waiting...")
        time.sleep(5)
        main() # Retry

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("stopping reactor")
