# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Ansispire, please report it
**privately** rather than opening a public GitHub issue.

**Contact**: [claude@taoziyoyo.com](mailto:claude@taoziyoyo.com)

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (a minimal, self-contained reproduction is best)
- Affected components: control plane (`controller/semaphore/`), audit plane
  (`controller/audit/`), EDA reactor (`controller/audit/reactor.py`), data
  plane (`roles/`, `playbooks/`), or bootstrap (`bootstrap.yml`)
- Any suggested mitigation or patch

We will acknowledge receipt within 5 business days and aim to provide a
response or remediation plan within 30 days. Critical vulnerabilities
affecting production deployments will be prioritized.

## Scope

In scope:

- Authentication / authorization bypass in the control plane
- Audit log tampering, replay, or loss
- Token leakage (e.g. across rsync boundaries, between containers, into
  state directories that are not properly excluded)
- Privilege escalation in the data plane (roles / playbooks)
- Bootstrap credential exposure (e.g. via logs, error messages, on-disk
  artefacts that should be ephemeral)
- Insecure defaults that a follower-of-the-Quickstart would be exposed to

Out of scope:

- Misconfigurations in user-supplied inventory or vault contents
- Vulnerabilities in upstream dependencies — please report to the upstream
  project first; we will track and rebase once upstream releases a fix
- DoS via resource exhaustion against a single non-redundant test instance
- Issues in code under `docs/reviews/_archive/` (historical material;
  superseded code paths)

## Coordinated Disclosure

We follow a 90-day coordinated disclosure window by default. If a fix is
shipped earlier, public disclosure can be earlier; if more time is needed
for a complex remediation, we will coordinate with the reporter.

Credit is given to reporters in the changelog unless they request otherwise.
