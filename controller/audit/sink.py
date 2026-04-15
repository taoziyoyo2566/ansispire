#!/usr/bin/env python3
"""Minimal audit sink — append Semaphore webhook POSTs to a JSONL file.

Stdlib-only (http.server) so the container has no extra deps.

Endpoints:
  GET  /healthz   — liveness probe, returns "ok"
  POST /event     — accepts any JSON body; appends a line with a wall-clock
                    timestamp and the client IP to AUDIT_LOG.

Any non-JSON body is still recorded (as a quoted string) so that a
misconfigured sender cannot silently lose audit coverage.
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG_PATH = os.environ.get("AUDIT_LOG", "/var/log/semaphore/events.jsonl")
PORT = int(os.environ.get("AUDIT_PORT", "3010"))


def _append(record: dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/event":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = raw.decode("utf-8", errors="replace")
        _append({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "remote": self.client_address[0],
            "path": self.path,
            "ua": self.headers.get("User-Agent", ""),
            "payload": payload,
        })
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        # Silence default stderr access logs — audit trail lives in JSONL.
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"audit-sink listening on 0.0.0.0:{PORT}, writing to {LOG_PATH}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
