# Feature: Audit Plane

## Overview
The Audit Plane ensures a tamper-proof, reliable trace of all management actions performed in the Ansispire system. It decouples event capture from core management logic.

## Key Triggers
- Any action in the Semaphore API (login, project update, key creation).
- Relay heartbeat (sent every 60s).

## Dependencies
- **Upstream**: Semaphore REST API (`/api/events`).
- **Downstream**: Audit Sink (`HTTP POST`).

## Data Flow Summary
`Semaphore` → `relay.py` (polling w/ pagination) → `sink.py` (collection) → `events.jsonl` (artifact).

## Critical Guarantees
- Zero data loss during relay restarts (via backfill pagination).
- Decoupled persistence (Sink is independent of Controller).
