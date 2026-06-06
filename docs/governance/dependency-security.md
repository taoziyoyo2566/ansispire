# Dependency & Image Security Governance

> **Scope of this document**: WU-1 of TASK-009 — **version truth + release-freeze model** only.
> Vulnerability scanning (WU-2), compatibility matrix (WU-3), Semaphore upstream policy (WU-4),
> and waiver rules (WU-5) live in sibling docs created by their own work units.
> Plan: [`docs/reviews/feat-dependency-security-governance/plan-2026-06-03.md`](../reviews/feat-dependency-security-governance/plan-2026-06-03.md).

This doc answers two questions the repo could not previously answer with evidence:

1. **Which file is the authoritative version source for each surface?** (no more "grep three places and guess")
2. **What is the reproducible set we ship / audit**, as distinct from the loose floor contributors install against?

---

## 1. Two version modes

The repo deliberately runs **two** version postures. Conflating them is the root of "works on my machine":

| Mode | Audience | Form | Where |
|---|---|---|---|
| **Dev floor** | contributors / local setup | `>=` lower bounds — "at least this, newer is fine" | `requirements.txt`, `pyproject.toml` optional-deps |
| **Release freeze** | CI gate / release cut / security audit | exact, reproducible resolved set (pins + digests) | freeze carriers in §3 |

- **Dev floor stays loose on purpose** (W-R13(b) / plan §7): pinning every contributor surface tightly makes onboarding brittle for zero security gain. The floor only needs to keep a fresh checkout *buildable*.
- **Release freeze is exact on purpose**: a CVE scan, a "what did we ship", or a rollback is only meaningful against a resolved set, not a `>=` range.

**Resolved open decision (plan §4 WU-1)**: release freeze applies to **CI / release / audit only**, *not* to all local development. Rationale above. If a contributor wants the exact set, they opt in by installing from the freeze carrier (§3); they are not forced to.

---

## 2. Versioned-surface inventory

Every versioned surface, its single authoritative source, and its current posture:

| Surface | SSOT file | Current form | Freeze carrier (release mode) |
|---|---|---|---|
| Local Python toolchain (ansible-core, lint, molecule, libs) | `requirements.txt` + `pyproject.toml` `[project.optional-dependencies]` | `>=` floors | **`uv.lock`** (see §3) |
| Ansible collections | `requirements.yml` | **already exact-pinned** (`community.general 12.6.0`, `community.mysql 4.2.0`, `community.docker 5.2.0`, `ansible.posix 2.1.0`) | `requirements.yml` itself is the freeze |
| Semaphore control-plane image | `config/manifest.yml` `ansispire_versions.semaphore_pinned` | tag pin (`v2.18.2`) | tag pin → **+ digest** (see §3) |
| Upstream Python base image (audit) | `config/manifest.yml` `audit_python_pinned` | tag pin (`3.12-alpine`) | tag pin → **+ digest** |
| Baked audit images (`ansispire/audit-*`) | `config/manifest.yml` `audit_baked_pinned` | tag pin (mirrors python base) | self-built digest at release tag |

**SSOT rule**: edit the version in the SSOT column *only*. Resolved/derived values (`ansispire_versions.semaphore`, `…audit_python`) and rendered `.env` blocks are computed downstream — never hand-edit them.

---

## 3. Freeze carriers — chosen, with rationale

### 3.1 Python → `uv.lock` (not a parallel constraints file)

**Decision**: the Python release-freeze carrier is **`uv.lock`**.

**Why (W-R18 framework-best-practice check)**: `pyproject.toml` already declares `[tool.uv]` with `dev-dependencies` — **uv is the adopted package manager**. uv's native lockfile (`uv.lock`) is the idiomatic reproducible-resolution artifact. Introducing a *second* freeze mechanism (`pip-compile`/`constraints.txt`, a hand-written release manifest) on top of an already-uv project would be the exact "layer a parallel mechanism on the existing tool" anti-pattern W-R18(b) warns against. So we align with uv rather than invent.

**Generation** (run in an environment that has `uv` + network — see §5 boundary):

```bash
uv lock                 # resolve pyproject + requirements into uv.lock
git add uv.lock
# commit on the release-cut branch; uv.lock is the reproducible Python set
```

**Consumption**:

```bash
uv sync --frozen        # install the exact locked set (CI / release / audit)
```

> **Status**: `uv.lock` is **not yet committed** — generating it requires `uv` + dependency-resolution network access, which the current planning workspace lacks (no `uv` binary, no daemon). This is a WU-1 follow-up to run in a provisioned env, not a doc gap. Until then the Python release set is *declared* (this doc) but not yet *materialized*.

### 3.2 Collections → `requirements.yml` is already the freeze

`requirements.yml` already pins exact versions. No new carrier needed; it serves as both floor and freeze. Bumps go through the normal review + (WU-3) compatibility check.

### 3.3 Container images → tag pin **plus digest** at release

Tag pins (`v2.18.2`, `3.12-alpine`) are mutable upstream. For a defensible release/audit set, a release cut additionally records the **immutable digest**:

```bash
docker buildx imagetools inspect semaphoreui/semaphore:v2.18.2 --format '{{.Manifest.Digest}}'
docker buildx imagetools inspect python:3.12-alpine          --format '{{.Manifest.Digest}}'
```

Record the `sha256:…` digests in the release changelog (and, when WU-2 lands, the scan report). `config/manifest.yml` stays tag-based for day-to-day (compose does not auto-pull → tags are effectively frozen between explicit pulls); the digest is the *release-evidence* layer, not a daily-edit surface.

---

## 4. SSOT-per-surface quick table (for future agents)

> "Where do I change version X?" — one answer per surface, no guessing.

| I want to change… | Edit only… | Then… |
|---|---|---|
| ansible-core / lint / molecule / a Python lib floor | `requirements.txt` (or `pyproject.toml` optional-deps) | re-`uv lock` on release branch |
| a collection version | `requirements.yml` | re-verify per WU-3 |
| Semaphore image | `config/manifest.yml` `semaphore_pinned` | WU-4 upgrade policy + `make test-api-contract` |
| audit Python base image | `config/manifest.yml` `audit_python_pinned` | re-bake audit images, re-record digest |
| ports | `config/manifest.yml` `ansispire_ports.*` | `make manifest-sync` |

---

## 5. Boundary — what this doc does NOT do

- **No vulnerability claim**: this is version *truth*, not CVE *truth*. "Is this set free of known High/Critical CVEs?" is WU-2 (`pip-audit`/`osv-scanner` for Python, `trivy`/`grype` for images).
- **No compatibility guarantee**: "supported together" is WU-3's matrix. This doc declares the *set*, not its tested-compatible *status*.
- **No Semaphore upgrade ritual**: bumping `semaphore_pinned` safely is WU-4.
- **No waiver mechanism**: WU-5.
- **No `uv.lock` materialized yet**: requires a provisioned env (uv + network); see §3.1 status.

---

## 6. Acceptance (WU-1 slice of plan §5)

WU-1 is complete when:

- [x] Every versioned surface has one declared SSOT (§2).
- [x] Dev-floor vs release-freeze are defined, with the freeze carrier chosen per surface (§1, §3).
- [x] The "which file for which surface" map is published (§4).
- [ ] `uv.lock` is generated and committed on a release-cut branch *(blocked: needs uv + network; tracked as the WU-1 runtime follow-up)*.

Remaining plan WUs (WU-2 scanners → WU-3 matrix → WU-4 Semaphore policy → WU-5 waivers) are out of this slice; see plan §6 order.
