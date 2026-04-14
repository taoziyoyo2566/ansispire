# callback_plugins/human_log.py
#
# ⚠ Teaching-oriented callback — demonstrates callback-plugin structure and event hooks.
#   Minimal robustness is in place, so this can be treated as an "enable-and-try"
#   example, but it is not recommended for production.
#
# Known limitations:
#   - Uses Unicode symbols (✓ ✗ ▶) — a few terminals may not render them
#   - Does not implement the full v2_runner_on_* event set (e.g. item_on_ok, item_on_failed)
#
# Enable via ansible.cfg:
#   callbacks_enabled = human_log, timer
#
# Or as stdout_callback:
#   stdout_callback = human_log   # replaces the default minimal/yaml output

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from datetime import datetime
from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"
    CALLBACK_NAME = "human_log"
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self):
        super().__init__()
        self._start_time = None
        self._task_start_time = None

    def _elapsed(self):
        """Safely compute task elapsed time; returns 0 if task_start_time is uninitialized."""
        if self._task_start_time is None:
            return 0.0
        return (datetime.now() - self._task_start_time).total_seconds()

    # ── Play ──────────────────────────────────────────────────────────────────
    def v2_playbook_on_start(self, playbook):
        self._start_time = datetime.now()
        self._display.display(
            f"\n{'='*60}\n  Playbook started at {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}",
            color="cyan"
        )

    def v2_playbook_on_play_start(self, play):
        self._display.display(f"\n▶ PLAY: {play.get_name()}", color="bright blue")

    # ── Task ──────────────────────────────────────────────────────────────────
    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_start_time = datetime.now()

    def v2_runner_on_ok(self, result):
        # A skipped=True result can still arrive via the ok event — treat as skipped.
        if result._result.get('skipped', False):
            return
        host = result._host.get_name()
        task = result._task.get_name()
        changed = result._result.get('changed', False)
        symbol = "↻" if changed else "✓"
        color = "yellow" if changed else "green"
        self._display.display(f"  {symbol} [{host}] {task} ({self._elapsed():.1f}s)", color=color)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        task = result._task.get_name()
        msg = result._result.get("msg", result._result.get("stderr", ""))
        prefix = "  ! (ignored)" if ignore_errors else "  ✗"
        color = "dark gray" if ignore_errors else "red"
        self._display.display(f"{prefix} [{host}] FAILED: {task} — {msg}", color=color)

    def v2_runner_on_skipped(self, result):
        host = result._host.get_name()
        task = result._task.get_name()
        self._display.display(f"  - [{host}] skipped: {task}", color="dark gray")

    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        msg = result._result.get("msg", "")
        self._display.display(f"  ! [{host}] UNREACHABLE: {msg}", color="red")

    # ── Stats ─────────────────────────────────────────────────────────────────
    def v2_playbook_on_stats(self, stats):
        total = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        self._display.display(
            f"\n{'='*60}\n  Playbook completed in {total:.1f}s\n{'='*60}",
            color="cyan"
        )
        for host in sorted(stats.processed.keys()):
            s = stats.summarize(host)
            line = (
                f"  {host:30s}  "
                f"ok={s['ok']:3d}  changed={s['changed']:3d}  "
                f"failed={s['failures']:3d}  skipped={s['skipped']:3d}  "
                f"unreachable={s['unreachable']:3d}"
            )
            color = "red" if s['failures'] or s['unreachable'] else "green"
            self._display.display(line, color=color)
