# callback_plugins/human_log.py
#
# ⚠ 教学演示型 Callback — 展示 Callback 插件的结构和事件钩子
#   已做最小健壮性处理，可作为"可启用的示例"，但不建议直接用于生产。
#
# 已知局限:
#   - 使用 Unicode 符号（✓ ✗ ▶），极少数终端可能不支持
#   - 不实现完整的 v2_runner_on_* 事件集（如 item_on_ok/item_on_failed）
#
# 启用方式（ansible.cfg）:
#   callbacks_enabled = human_log, timer
#
# 或作为 stdout_callback:
#   stdout_callback = human_log   # 替换默认 minimal/yaml 输出

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
        """安全计算 task 耗时，task_start_time 未初始化时返回 0"""
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
        # result._result.get('skipped') が True の場合も ok イベントで来ることがある
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
