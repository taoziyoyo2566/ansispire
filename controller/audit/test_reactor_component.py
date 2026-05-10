#!/usr/bin/env python3
"""L3 component test — reactor → mock Semaphore HTTP contract.

Validates the outbound API call shape (method/path/Bearer/body) against an
in-process http.server stub. No docker, no real Semaphore. See
docs/test-specs/eda-reactor-component.md for the full spec.
"""

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import reactor

PROJECT_ID = 7
TEMPLATE_ID = 42
PROJECT_NAME = "ansispire"
TEMPLATE_NAME = "Auto Remediation: Disk Cleanup"


# Per-test mock state — populated in setUp via setattr to avoid a global mess.
class _MockState:
    received: list
    projects: list
    templates: list


STATE = _MockState()


class _Handler(BaseHTTPRequestHandler):
    def _record(self, body=None):
        STATE.received.append({
            "method": self.command,
            "path": self.path,
            "auth": self.headers.get("Authorization", ""),
            "body": body,
        })

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._record()
        if self.path == "/api/projects":
            self._send(200, STATE.projects)
        elif self.path == f"/api/project/{PROJECT_ID}/templates":
            self._send(200, STATE.templates)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else None
        except Exception:
            body = raw.decode("utf-8", errors="replace")
        self._record(body=body)
        if self.path == f"/api/project/{PROJECT_ID}/tasks":
            self._send(201, {"id": 1, "status": "waiting"})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args, **kwargs):
        return  # silence stderr access logs


class TestReactorComponent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self):
        # Fresh per-test state
        STATE.received = []
        STATE.projects = [{"id": PROJECT_ID, "name": PROJECT_NAME}]
        STATE.templates = [{"id": TEMPLATE_ID, "name": TEMPLATE_NAME}]
        # Point reactor at the mock; reset module-level cache
        reactor.SEMAPHORE_URL = f"http://127.0.0.1:{self.port}"
        reactor.SEMAPHORE_TOKEN = "test-token-xyz"
        reactor.TEMPLATE_CACHE = {}

    # ── K1 ────────────────────────────────────────────────────────────
    def test_K1_happy_path_request_contract(self):
        action = {
            "type": "semaphore_api",
            "project_name": PROJECT_NAME,
            "template_name": TEMPLATE_NAME,
        }
        reactor.trigger_semaphore_task(action)

        self.assertEqual(len(STATE.received), 3,
                         f"expected exactly 3 outbound requests, got {STATE.received}")

        r0, r1, r2 = STATE.received

        # Bearer on every call
        for r in (r0, r1, r2):
            self.assertEqual(r["auth"], "Bearer test-token-xyz")

        # Sequence
        self.assertEqual((r0["method"], r0["path"]), ("GET", "/api/projects"))
        self.assertEqual((r1["method"], r1["path"]),
                         ("GET", f"/api/project/{PROJECT_ID}/templates"))
        self.assertEqual((r2["method"], r2["path"]),
                         ("POST", f"/api/project/{PROJECT_ID}/tasks"))

        # POST body shape
        self.assertEqual(r2["body"], {"template_id": TEMPLATE_ID})

    # ── K2 ────────────────────────────────────────────────────────────
    def test_K2_template_id_cache_skips_repeat_lookup(self):
        action = {
            "type": "semaphore_api",
            "project_name": PROJECT_NAME,
            "template_name": TEMPLATE_NAME,
        }
        reactor.trigger_semaphore_task(action)
        first_call_count = len(STATE.received)
        self.assertEqual(first_call_count, 3)

        STATE.received.clear()
        reactor.trigger_semaphore_task(action)
        # Second call: project lookup still re-issued (no project cache
        # in current reactor), template lookup IS cached → only 2 requests
        paths = [(r["method"], r["path"]) for r in STATE.received]
        self.assertEqual(paths, [
            ("GET", "/api/projects"),
            ("POST", f"/api/project/{PROJECT_ID}/tasks"),
        ], f"expected GET projects + POST tasks (template cached), got {paths}")

    # ── K3 ────────────────────────────────────────────────────────────
    def test_K3_template_not_found_does_not_post(self):
        STATE.templates = [{"id": 999, "name": "Some Other Template"}]
        action = {
            "type": "semaphore_api",
            "project_name": PROJECT_NAME,
            "template_name": TEMPLATE_NAME,  # not in mock
        }
        reactor.trigger_semaphore_task(action)
        posts = [r for r in STATE.received if r["method"] == "POST"]
        self.assertEqual(posts, [], "POST must not be sent when template_name unresolved")

    # ── K4 ────────────────────────────────────────────────────────────
    def test_K4_project_not_found_does_not_lookup_templates(self):
        STATE.projects = [{"id": 99, "name": "different-project"}]
        action = {
            "type": "semaphore_api",
            "project_name": PROJECT_NAME,  # not in mock
            "template_name": TEMPLATE_NAME,
        }
        reactor.trigger_semaphore_task(action)
        # Should only see GET /api/projects, then abort
        paths = [(r["method"], r["path"]) for r in STATE.received]
        self.assertEqual(paths, [("GET", "/api/projects")],
                         f"expected only /api/projects when project unresolved, got {paths}")

    # ── K5 ────────────────────────────────────────────────────────────
    def test_K5_empty_token_aborts_before_post(self):
        reactor.SEMAPHORE_TOKEN = ""
        action = {
            "type": "semaphore_api",
            "project_name": PROJECT_NAME,
            "template_name": TEMPLATE_NAME,
        }
        reactor.trigger_semaphore_task(action)
        posts = [r for r in STATE.received if r["method"] == "POST"]
        self.assertEqual(posts, [], "POST must not be sent when SEMAPHORE_TOKEN is empty")


if __name__ == "__main__":
    unittest.main()
