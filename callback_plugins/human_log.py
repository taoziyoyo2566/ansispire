# callback_plugins/human_log.py — 自定义 Callback 插件示例
#
# Callback 插件: 监听 Ansible 事件（task 开始/结束、play 开始/结束等）
# 用途: 自定义输出格式、发送通知（Slack/PagerDuty）、写入数据库
#
# 启用方式（在 ansible.cfg 中）:
#   [defaults]
#   callbacks_enabled = human_log, timer, profile_tasks
#
# 或设置为 stdout_callback（替换默认输出）:
#   stdout_callback = human_log
#
# 内置可用的 callback:
#   timer          — 显示总执行时间
#   profile_tasks  — 显示每个 task 耗时
#   profile_roles  — 显示每个 role 耗时
#   yaml           — YAML 格式输出（比默认更易读）
#   json           — JSON 格式输出（机器解析）
#   unixy          — 简洁的单行输出
#   debug          — 详细调试输出
#   null           — 抑制所有输出

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from datetime import datetime
from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    """
    自定义 callback: 以人类友好格式记录关键事件，并统计耗时。
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"     # notification: 附加到默认 callback 上
    CALLBACK_NAME = "human_log"
    CALLBACK_NEEDS_ENABLED = True      # 必须在 ansible.cfg 中显式开启

    def __init__(self):
        super().__init__()
        self.start_time = None
        self.task_start_time = None

    # ── Play 级事件 ───────────────────────────────────────────────────────────
    def v2_playbook_on_start(self, playbook):
        self.start_time = datetime.now()
        self._display.display(
            f"\n{'='*60}\n  Playbook started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}",
            color="cyan"
        )

    def v2_playbook_on_play_start(self, play):
        self._display.display(f"\n▶ PLAY: {play.get_name()}", color="bright blue")

    # ── Task 级事件 ───────────────────────────────────────────────────────────
    def v2_playbook_on_task_start(self, task, is_conditional):
        self.task_start_time = datetime.now()

    def v2_runner_on_ok(self, result):
        host = result._host.get_name()
        task = result._task.get_name()
        elapsed = (datetime.now() - self.task_start_time).total_seconds() if self.task_start_time else 0
        changed = result._result.get("changed", False)

        symbol = "✓" if not changed else "↻"
        color = "green" if not changed else "yellow"
        self._display.display(f"  {symbol} [{host}] {task} ({elapsed:.1f}s)", color=color)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        task = result._task.get_name()
        msg = result._result.get("msg", "")
        self._display.display(f"  ✗ [{host}] FAILED: {task} — {msg}", color="red")

    def v2_runner_on_skipped(self, result):
        host = result._host.get_name()
        task = result._task.get_name()
        self._display.display(f"  - [{host}] SKIPPED: {task}", color="dark gray")

    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        self._display.display(f"  ! [{host}] UNREACHABLE", color="red")

    # ── Playbook 结束 ─────────────────────────────────────────────────────────
    def v2_playbook_on_stats(self, stats):
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        self._display.display(
            f"\n{'='*60}\n  Playbook completed in {elapsed:.1f}s\n{'='*60}",
            color="cyan"
        )
