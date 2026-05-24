# Plan — Complete RHEL-family support in vps_runner onboard

**Date:** 2026-05-24
**Branch:** `feat/vps-manager-v2`
**Level:** 🔴 [L2] — completes data-plane support for a whole OS family in `onboard.yml`; changes the onboard contract for RHEL hosts.
**Trigger:** live onboard of `hk-alm9` (AlmaLinux 9) surfaced the RHEL gap class one layer at a time (host-key → fail2ban/EPEL → predicted firewalld/SELinux). User feedback: stop fixing one error per round; audit the whole class.

## §0 Pre-execution checklist (W-R18 framework best-practice pre-check)

| Need | Native pattern checked | Conclusion |
|---|---|---|
| Enable EPEL on RHEL | `roles/common` seeds `epel-release` via `_common__os_packages`; `ansible.builtin.dnf` | matches — already done in onboard.yml round13; this plan adds resilience |
| RHEL firewall | Debian path uses `community.general.ufw`; RHEL equivalent is `ansible.posix.firewalld` (verified installed, posix 2.1.0) | matches — mirror UFW task set with firewalld |
| Non-22 SSH port under SELinux | `community.general.seport` (verified installed) labels tcp/1156 as `ssh_port_t` | matches — required before sshd binds 1156 under enforcing |
| Optional-feature failure policy | `modify.yml` supports `fail2ban: {enabled: true}` toggle → deferred fail2ban is a supported state | matches — fail-soft is architecturally consistent |

**Direction: matches.** No anti-pattern; all four build on existing project/collection patterns.

## §1 Purpose / scope

Make `onboard.yml` complete and resilient on RHEL family (Rocky/Alma 9), so a fresh RHEL VPS onboards in one run without hitting Debian-only assumptions.

**In scope (3 work units):**

- **WU1 — EPEL/fail2ban resilience.** The live run failed at `Install fail2ban` with `Failed to download metadata for repo 'epel' … all mirrors tried`. Docker CE (different repo) succeeded, so it's specifically EPEL/Fedora-mirror reachability (transient flakiness / HK→Fedora / IPv6).
  - (a) Add `retries/until/delay` to the EPEL-enable + fail2ban-install tasks (handles transient mirror hiccups; mirrors the retry pattern already at onboard.yml:520).
  - (b) Wrap EPEL-enable + fail2ban-install in `block/rescue`: on persistent failure set `vps_fail2ban_deferred=true`, emit a prominent warning, and **continue** (fail-soft). fail2ban is optional hardening and re-addable via `modify --toggle-fail2ban on`. The run summary/`record_run` notes the deferral.

- **WU2 — firewalld support (RedHat family).** All firewall tasks are currently `os_family == Debian`/UFW gated → on RHEL nothing opens the managed SSH port (1156), so `Wait for managed SSH port` would time out if firewalld is active. Mirror the UFW task set with `ansible.posix.firewalld`, gated on `os_family == RedHat` + firewalld present/active: allow managed port, keep bootstrap port open, allow requested TCP ports + http/https, set zone target, reload; close bootstrap port after final validation. Skip cleanly when firewalld is absent/inactive (some images use nftables/cloud SG only).

- **WU3 — SELinux managed-SSH-port label.** Under SELinux enforcing, sshd cannot bind a non-`ssh_port_t` port; the SSH migration to 1156 would silently fail to listen → `Wait for managed SSH port` times out. Add `community.general.seport` (name=managed_port, proto=tcp, setype=ssh_port_t) **before** the transitional sshd reload, gated on `os_family == RedHat` + SELinux enabled (reuse the getenforce probe already in the Docker block, or add a dedicated one). Idempotent; harmless if permissive/disabled.

**Out of scope:** Alpine; nftables-direct hosts; non-SSH SELinux contexts; changing Debian behavior.

## §2 Decision rationale

- **Defensive, not host-specific.** WU2/WU3 are written to no-op when firewalld is inactive / SELinux not enforcing, so the same code is correct whether or not *this* host needs them — avoids another round-trip to read host state and makes onboard correct for all RHEL hosts.
- **fail-soft for fail2ban only.** Core onboarding (Docker, managed user, SSH lockdown, firewall) stays hard-fail; only the optional fail2ban hardening degrades gracefully, because the project already supports adding it later via `modify`.

## §3 Verification (W-R15 per WU)

- Gate 2: `ansible-playbook --syntax-check` + `ansible-lint` (production profile, expect 0/0) after each WU.
- Gate 3: live re-run `make vps-add-host` against `hk-alm9` (operator-driven, needs password) → expect PLAY RECAP `failed=0`, managed channel reachable on 1156, host_vars status=active. fail2ban either installs (EPEL transient) or is reported deferred.
- Unit: existing suite stays green (the one pre-existing R12 audit-rules failure excepted).

## §4 Open question for the user (scope gate)

Confirmed by the live run: **WU1** (fail2ban/EPEL). **WU2/WU3** are predicted-but-unconfirmed (depend on this host's firewalld state / SELinux mode). Two paths:
- **Full pass (WU1+2+3)** — one more re-run completes regardless of host state; builds correct RHEL support even if this host doesn't strictly need WU2/WU3.
- **Confirmed-only (WU1)** — fix EPEL/fail2ban, re-run, and only build WU2/WU3 if the host actually blocks there (your earlier "re-run to see" methodology; risks one more wall).
