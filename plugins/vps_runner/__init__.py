"""vps_runner — Ansible-native VPS lifecycle plugin.

Replaces the legacy vps_manager plugin's anti-pattern implementation
(per-task subprocess + custom inventory state) with native Ansible
patterns (ansible-runner + standard inventory + Ansible forks).

See docs/reviews/feat-vps-manager-v2/plan-2026-05-16.md for the design.
"""
