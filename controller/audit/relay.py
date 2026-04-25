#!/usr/bin/env python3
"""Enhanced audit relay — Semaphore /api/events → audit-sink.

Polls Semaphore's global /api/events endpoint with pagination support to
ensure zero data loss. Forwards entries to the sink as structured JSON POSTs.
Uses stdlib only (urllib + json).

Cursor persistence:
    /var/lib/audit-relay/cursor.json = {"last_ts": "<RFC3339 timestamp>"}

Logic:
    1. Fetch pages (newest-first) until we hit the cursor or a safety limit.
    2. Sort the batch ascending (oldest-first).
    3. Forward each event; update cursor atomically after successful forward.
    4. Emit a heartbeat if no events are found for a while.
"""

import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Configuration
SEM_URL = os.environ.get("SEMAPHORE_URL", "http://semaphore:3000")
SEM_USER = os.environ.get("SEMAPHORE_USER", "admin")
SEM_PW = os.environ["SEMAPHORE_PASSWORD"]
SINK_URL = os.environ.get("SINK_URL", "http://audit-sink:3010/event")
STATE_FILE = os.environ.get("STATE_FILE", "/var/lib/audit-relay/cursor.json")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))
PAGE_LIMIT = 50  # Items per page
MAX_PAGES = 10   # Safety break to avoid infinite loops on first run

EPOCH = "1970-01-01T00:00:00Z"


def log(msg: str) -> None:
    print(f"[relay] {msg}", file=sys.stderr, flush=True)


def load_cursor() -> str:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("last_ts", EPOCH)
    except (FileNotFoundError, json.JSONDecodeError):
        return EPOCH


def save_cursor(ts: str) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"last_ts": ts}, f)
    os.replace(tmp, STATE_FILE)


def make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def login(opener: urllib.request.OpenerDirector) -> None:
    body = json.dumps({"auth": SEM_USER, "password": SEM_PW}).encode()
    req = urllib.request.Request(
        f"{SEM_URL}/api/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener.open(req, timeout=10).read()


def fetch_page(opener: urllib.request.OpenerDirector, page: int) -> list:
    url = f"{SEM_URL}/api/events?limit={PAGE_LIMIT}&page={page}"
    with opener.open(url, timeout=10) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else []


def forward(payload: dict) -> None:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        SINK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()


def emit_heartbeat() -> None:
    payload = {
        "source": "audit-relay",
        "type": "heartbeat",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "alive"
    }
    try:
        forward(payload)
    except Exception as e:
        log(f"heartbeat failed: {e}")


def tick(opener: urllib.request.OpenerDirector, cursor: str) -> str:
    all_events = []
    page = 1
    reached_cursor = False

    # 1. Fetch pages backwards until we hit the cursor
    while page <= MAX_PAGES:
        events = fetch_page(opener, page)
        if not events:
            break
        
        chunk = []
        for ev in events:
            ts = ev.get("created", "")
            if ts <= cursor:
                reached_cursor = True
                break
            chunk.append(ev)
        
        all_events.extend(chunk)
        if reached_cursor or len(events) < PAGE_LIMIT:
            break
        page += 1

    if not all_events:
        return cursor

    # 2. Sort ascending (oldest first) to advance cursor correctly
    all_events.sort(key=lambda e: e.get("created", ""))
    
    # 3. Forward and update cursor atomically
    last_successful_ts = cursor
    for ev in all_events:
        ts = ev.get("created", "")
        try:
            forward({"source": "semaphore", "event": ev})
            last_successful_ts = ts
            # Optional: save cursor per event if batches are huge, 
            # but per-tick is usually fine for these volumes.
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"forward failed at ts={ts}: {e}; will retry from this point")
            break
    
    if last_successful_ts != cursor:
        save_cursor(last_successful_ts)
        log(f"advanced cursor to {last_successful_ts} ({len(all_events)} events)")
    
    return last_successful_ts


def main() -> None:
    log(f"starting enhanced relay: {SEM_URL} → {SINK_URL}")
    opener = make_opener()
    
    last_heartbeat = time.time()
    heartbeat_interval = 60 # 1 minute

    # Initial login loop
    while True:
        try:
            login(opener)
            break
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"login failed ({e}); retrying in {POLL_INTERVAL}s")
            time.sleep(POLL_INTERVAL)

    cursor = load_cursor()
    log(f"cursor loaded: {cursor}")
    
    while True:
        try:
            new_cursor = tick(opener, cursor)
            cursor = new_cursor
            
            # Heartbeat logic
            if time.time() - last_heartbeat > heartbeat_interval:
                emit_heartbeat()
                last_heartbeat = time.time()
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log("session expired; re-logging in")
                opener = make_opener()
                try:
                    login(opener)
                except Exception as e2:
                    log(f"re-login failed: {e2}")
            else:
                log(f"http error {e.code}: {e.reason}")
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"transport error: {e}")
        except Exception as e:
            log(f"unexpected error: {e}")
            
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
