# Feature: EDA Reactor Core

## Overview
A lightweight Event-Driven Ansible (EDA) reaction engine that transforms audit logs into autonomous actions (self-healing or alerting).

## Key Triggers
- New entries in `events.jsonl` matching conditions in `rules.json`.

## Actions Supported
- **Webhook**: Forward alerts to external endpoints.
- **Shell**: Trigger Ansible playbooks or local scripts for remediation.

## Dependencies
- **Data Source**: `events.jsonl` (Audit Sink).
- **Rulebook**: `extensions/eda/rules.json`.

## Design Philosophy
- **Lightweight**: Zero external dependencies (Python stdlib + subprocess).
- **Secure**: Actions limited to predefined shell commands and webhook targets.
