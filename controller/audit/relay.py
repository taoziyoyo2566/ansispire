#!/usr/bin/env python3
"""Round 9 audit relay — Semaphore /api/events → audit-sink.

Polls Semaphore's global /api/events endpoint and forwards any entries newer
than the last cursor to the sink as structured JSON POSTs. Uses stdlib only
(urllib + json) to match the sink's zero-dep posture.

Cursor persistence:
    /var/lib/audit-relay/cursor.json = {"last_ts": "<RFC3339 timestamp>"}

Semaphore /api/events ordering is newest-first. We sort ascending by
`created` and forward anything strictly newer than the cursor. On the first
run, the cursor starts at epoch so the full event history is replayed
once — this is acceptable for a learning sink.
"""

import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request

SEM_URL = os.environ.get("SEMAPHORE_URL", "http://semaphore:3000")
SEM_USER = os.environ.get("SEMAPHORE_USER", "admin")
SEM_PW = os.environ["SEMAPHORE_PASSWORD"]
SINK_URL = os.environ.get("SINK_URL", "http://audit-sink:3010/event")
STATE_FILE = os.environ.get("STATE_FILE", "/var/lib/audit-relay/cursor.json")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "5"))

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


def fetch_events(opener: urllib.request.OpenerDirector) -> list:
    with opener.open(f"{SEM_URL}/api/events", timeout=10) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else []


def forward(event: dict) -> None:
    body = json.dumps({"source": "semaphore", "event": event}).encode()
    req = urllib.request.Request(
        SINK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()


def tick(opener: urllib.request.OpenerDirector, cursor: str) -> str:
    events = fetch_events(opener)
    # Ascending by `created` so we forward oldest→newest and advance cursor safely.
    events.sort(key=lambda e: e.get("created", ""))
    advanced = cursor
    for ev in events:
        ts = ev.get("created", "")
        if ts <= cursor:
            continue
        try:
            forward(ev)
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"forward failed at ts={ts}: {e}; will retry next tick")
            return advanced
        advanced = ts
    if advanced != cursor:
        save_cursor(advanced)
        log(f"advanced cursor to {advanced}")
    return advanced


def main() -> None:
    log(f"starting: {SEM_URL} → {SINK_URL}, poll={POLL_INTERVAL}s")
    opener = make_opener()
    # Retry login until Semaphore is reachable (e.g. during compose start).
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
            cursor = tick(opener, cursor)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log("session expired; re-logging in")
                opener = make_opener()
                try:
                    login(opener)
                except urllib.error.URLError as e2:
                    log(f"re-login failed: {e2}")
            else:
                log(f"http error {e.code}: {e.reason}")
        except (urllib.error.URLError, TimeoutError) as e:
            log(f"transport error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
