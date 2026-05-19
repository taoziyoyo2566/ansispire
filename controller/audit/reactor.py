#!/usr/bin/env python3
"""Advanced EDA Reactor v2.6 — Observability & Robustness.

Supports '_contains' matching, dynamic resolution, verbose diagnostic logging,
mtime-aware rules cache, cursor-persisted jsonl tail with copytruncate-safe
truncation handling (seek-to-start, not seek-to-EOF), per-rule exception
isolation, and a fatal-restart outer loop (no recursion).

v2.5 → v2.6 fixes (Codex second-pass review, 2026-05-19):
- load_cursor() now returns Optional[int]: None means the cursor file is
  absent (fresh boot → seek EOF); int (including 0) means the cursor file
  is present and authoritative. Previously, absent and present-but-zero
  collapsed to "0" and both fell through to seek(EOF), so a reactor crash
  immediately after save_cursor(0) (post-truncate marker) would skip the
  entire post-rotate file on the next boot.
- process_event: isinstance(rule, dict) guard at the top of the per-rule
  loop. Previous v2.5 except-block called rule.get(...) on whatever object
  match_rule rejected, re-raising AttributeError on non-dict rules and
  killing the tail loop.

v2.4 → v2.5 fixes (cross-pollinated from fix/ansible-docs-review-remediation
review, 2026-05-19):
- Truncation handling at startup AND during run: seek(0), not seek(EOF).
  Previous EOF-seek silently dropped events between truncation and reactor
  restart — defeating the whole point of cursor persistence.
- Per-tick `f.tell() > size` detection: catches `logrotate copytruncate`
  events that happen WHILE reactor is running. Previous version only
  checked truncation at startup, leaking events until next restart.
- match_rule wrapped in try/except per rule: a malformed rule cannot
  bring down the tail loop.
- _contains values coerced via str() — defense in depth for hand-edited
  rules.json that bypassed `make test-rules-schema`.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Optional

# Configuration
JSONL_PATH = os.environ.get("JSONL_PATH", "/var/log/semaphore/events.jsonl")
RULES_PATH = os.environ.get("RULES_PATH", "/etc/ansispire/eda/rules.json")
SCHEMA_PATH = os.environ.get("EVENTS_SCHEMA_PATH", "/etc/ansispire/eda/events.schema.json")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "1.0"))
WEBHOOK_URL = os.environ.get("EDA_WEBHOOK_URL", "")

# Rules cache — only reload when mtime changes AND at least
# RULES_MIN_RELOAD_INTERVAL seconds have elapsed since the previous
# reload. Defaults amount to: at most one reload per minute even under
# rapid rules.json churn.
RULES_MIN_RELOAD_INTERVAL = float(os.environ.get("RULES_MIN_RELOAD_INTERVAL", "30"))

# Cursor persistence — `tail -F` from the last byte we successfully read
# instead of jumping to EOF on every restart. Disable by setting
# CURSOR_FILE="".
CURSOR_FILE = os.environ.get("CURSOR_FILE", "/var/lib/audit-reactor/cursor")
CURSOR_FLUSH_INTERVAL = float(os.environ.get("CURSOR_FLUSH_INTERVAL", "5.0"))

# Fatal-restart backoff — when the inner loop dies (e.g. JSONL_PATH
# disappeared while reactor was running) wait this long before retrying.
FATAL_RESTART_BACKOFF = float(os.environ.get("FATAL_RESTART_BACKOFF", "5.0"))

# Semaphore API Config
SEMAPHORE_URL = os.environ.get("SEMAPHORE_URL", "http://semaphore:3000")
SEMAPHORE_TOKEN = os.environ.get("SEMAPHORE_API_TOKEN", "")

LAST_TRIGGERED = {}
TEMPLATE_CACHE = {}

# Rules cache state — populated lazily by load_rules.
_RULES_CACHE = {"mtime": None, "loaded_at": 0.0, "rules": []}

def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] [reactor] {msg}", file=sys.stderr, flush=True)

def load_rules(force: bool = False) -> list:
    """Return parsed rules from RULES_PATH.

    Cached behaviour: hits disk only when (a) RULES_PATH mtime has changed
    since the last successful load AND (b) at least
    RULES_MIN_RELOAD_INTERVAL seconds have elapsed (rate-limit against
    runaway editor saves). Set force=True to bypass both gates (used at
    startup so cold-start always reads).
    """
    now = time.time()
    try:
        if not os.path.exists(RULES_PATH):
            if _RULES_CACHE["mtime"] is not None:
                log(f"rules file disappeared: {RULES_PATH}")
                _RULES_CACHE["mtime"] = None
                _RULES_CACHE["rules"] = []
            return _RULES_CACHE["rules"]
        mtime = os.path.getmtime(RULES_PATH)
        if not force \
                and _RULES_CACHE["mtime"] == mtime \
                and (now - _RULES_CACHE["loaded_at"]) < RULES_MIN_RELOAD_INTERVAL:
            return _RULES_CACHE["rules"]
        if not force \
                and _RULES_CACHE["mtime"] == mtime:
            # Mtime unchanged: refresh the loaded_at timestamp so we
            # don't restat on every poll, but reuse cached rules.
            _RULES_CACHE["loaded_at"] = now
            return _RULES_CACHE["rules"]
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        rules = data.get("rules", [])
        prev_count = len(_RULES_CACHE["rules"])
        _RULES_CACHE["rules"] = rules
        _RULES_CACHE["mtime"] = mtime
        _RULES_CACHE["loaded_at"] = now
        if force or prev_count != len(rules):
            log(f"rules loaded: {len(rules)} (mtime={int(mtime)})")
        else:
            log(f"rules reloaded: {len(rules)} (mtime changed)")
        return rules
    except Exception as e:
        log(f"error loading rules: {e}")
        return _RULES_CACHE["rules"]

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
            # str(value) defense: rules.schema.json restricts _contains values
            # to strings, but if a rule slipped past validation (e.g., rules.json
            # edited by hand without `make test-rules-schema`), avoid TypeError.
            if str(value) not in actual_val:
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

def trigger_webhook(action: dict, event_payload: dict) -> None:
    url = (action.get("url") or "").strip()
    name = action.get("name", "unnamed-webhook")
    if not url:
        log(f"webhook skipped: {name} has no url configured")
        return
    body = json.dumps({
        "rule_action": name,
        "event": event_payload.get("payload", {}).get("event", {}),
    }).encode()
    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            log(f"webhook fired: {name} → {url} status={resp.status}")
    except Exception as e:
        log(f"webhook failed: {name} → {url}: {e}")

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
        # Defense in depth: one malformed rule must not crash the whole
        # tail loop. Log + skip + continue to the next rule.
        if not isinstance(rule, dict):
            log(f"skipping malformed rule (expected dict, got "
                f"{type(rule).__name__}): {rule!r:.80s}")
            continue
        try:
            matched = match_rule(payload, rule)
        except Exception as e:
            log(f"rule evaluation failed ({rule.get('name', '<unnamed>')}): "
                f"{type(e).__name__}: {e}")
            continue
        if matched:
            log(f"MATCH FOUND: {rule.get('name')}")
            LAST_TRIGGERED[rule.get("name")] = time.time()
            for action in rule.get("actions", []):
                if action.get("type") == "semaphore_api":
                    trigger_semaphore_task(action)
                elif action.get("type") == "webhook":
                    trigger_webhook(action, payload)

def load_cursor() -> Optional[int]:
    """Return the persisted byte offset.

    - None: cursor persistence disabled OR cursor file does not yet exist
      (fresh boot; caller should seek to EOF to avoid dumping the backlog).
    - int (including 0): cursor file is present and authoritative — caller
      MUST honor the offset. 0 specifically means "we just observed a
      logrotate copytruncate; consume from the start of the new file."
    - -1: read failed for an unexpected reason; caller treats as EOF.
    """
    if not CURSOR_FILE:
        return None
    try:
        with open(CURSOR_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except FileNotFoundError:
        return None
    except Exception as e:
        log(f"cursor read failed ({CURSOR_FILE}): {e}; restarting from EOF")
        return -1  # sentinel: caller seeks to EOF


def save_cursor(offset: int) -> None:
    """Best-effort write of byte offset to CURSOR_FILE. Silent on failure
    (we'd rather skip an offset write than crash the tail loop)."""
    if not CURSOR_FILE:
        return
    try:
        os.makedirs(os.path.dirname(CURSOR_FILE), exist_ok=True)
        # Atomic-ish via .tmp swap to avoid torn writes on crash.
        tmp = f"{CURSOR_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(offset))
        os.replace(tmp, CURSOR_FILE)
    except Exception as e:
        log(f"cursor write failed ({CURSOR_FILE}): {e}")


def run_tail_loop() -> None:
    """One pass of the tail-and-react loop. Caller is responsible for
    restarting us if we raise — see main()."""
    if not os.path.exists(JSONL_PATH):
        log(f"warning: {JSONL_PATH} does not exist yet. waiting...")

    rules = load_rules(force=True)

    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        start = load_cursor()
        if start is None:
            # No cursor file → fresh boot. Don't dump the historical backlog.
            f.seek(0, os.SEEK_END)
            log(f"tail start: EOF (no cursor file)")
        elif start == -1:
            f.seek(0, os.SEEK_END)
            log(f"tail start: EOF (cursor unreadable, treating as fresh)")
        else:
            # Cursor file is present and authoritative. start==0 here means
            # "we just persisted a post-truncate marker" — we MUST seek(0),
            # not EOF, otherwise a restart between save_cursor(0) and the
            # first post-rotate readline skips the entire rotated file.
            try:
                size = os.path.getsize(JSONL_PATH)
                if start > size:
                    # Truncation detected at startup (logrotate copytruncate
                    # produced a smaller file). The post-truncation file
                    # holds fresh content from offset 0 — seek to the start
                    # so we consume new events instead of skipping them.
                    log(f"tail start: cursor {start} > file size {size}; "
                        f"truncation detected, seeking to start")
                    f.seek(0)
                    save_cursor(0)
                else:
                    f.seek(start)
                    log(f"tail start: cursor offset {start} (file size {size})")
            except Exception as e:
                log(f"tail start: stat failed ({e}); seeking to EOF")
                f.seek(0, os.SEEK_END)

        last_flush = time.time()
        while True:
            line = f.readline()
            if not line:
                time.sleep(POLL_INTERVAL)
                # mtime-gated cheap call — see load_rules.
                rules = load_rules()
                now = time.time()
                # Per-tick truncation detection: copytruncate while running.
                # Without this, the FD keeps reading past the new (smaller)
                # file size and returns empty, silently dropping post-rotate
                # events until the next reactor restart.
                try:
                    size = os.path.getsize(JSONL_PATH)
                except Exception:
                    size = None
                if size is not None and f.tell() > size:
                    log(f"tail running: offset {f.tell()} > file size {size}; "
                        f"truncation detected, seeking to start")
                    f.seek(0)
                    save_cursor(0)
                    last_flush = now
                    continue
                if CURSOR_FILE and (now - last_flush) >= CURSOR_FLUSH_INTERVAL:
                    save_cursor(f.tell())
                    last_flush = now
                continue
            process_event(line, rules)
            # Flush cursor opportunistically per processed line; the
            # time-based gate in the idle branch covers the no-event
            # case.
            now = time.time()
            if CURSOR_FILE and (now - last_flush) >= CURSOR_FLUSH_INTERVAL:
                save_cursor(f.tell())
                last_flush = now


def main() -> None:
    log(f"starting advanced reactor v2.5, monitoring {JSONL_PATH}")
    log(f"event schema: {schema_banner()}")
    log(f"rules: min reload interval={RULES_MIN_RELOAD_INTERVAL}s; cursor={CURSOR_FILE or '<disabled>'} flush_every={CURSOR_FLUSH_INTERVAL}s")
    # Outer loop: if the tail dies (file deleted, FS error, …) log and
    # retry after FATAL_RESTART_BACKOFF. No recursion — we want a flat
    # call stack so restarts don't slowly eat memory.
    while True:
        try:
            run_tail_loop()
        except KeyboardInterrupt:
            return
        except Exception as e:
            log(f"fatal error: {type(e).__name__}: {e}; restarting in {FATAL_RESTART_BACKOFF}s")
            time.sleep(FATAL_RESTART_BACKOFF)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
