"""vps_runner — Ansible-native VPS lifecycle plugin.

Uses ansible-runner + standard Ansible inventory (no subprocess wrapping,
no custom callback, no custom state file). Ansible-native concurrency
via `forks`. See docs/reference/feature-map/vps-runner.md for the spec.
"""
