# Evidence-Backed Planning

Use this before writing or materially changing a non-trivial plan, especially
when the plan depends on third-party tools, current best practice, APIs,
security guidance, operating systems, cloud/VPS providers, or live
infrastructure behavior.

## Core rule

Do not plan from memory when external knowledge is load-bearing.

Repo facts come from the repo. External facts come from current external
sources, preferably primary sources. If an external fact may have changed,
verify it before turning it into implementation guidance.

## Evidence pass before writing a plan

Before finalizing a plan, build a small evidence inventory:

| Item | Examples | Required action |
|---|---|---|
| Repo facts | current code, TODO, prior plans, feature maps | inspect local files |
| External tool behavior | Semaphore API/UI, Ansible modules, Docker behavior | check official docs or source |
| Security practice | SSH hardening, key handling, secret storage | check official/vendor/standards guidance |
| Runtime capability | daemon available, tool installed, service reachable | probe per `~/workspace/.agents/rules/environment-truth.md` |
| Operator decision | real VPS, credential owner, destructive run approval | record owner and gate |

The plan does not need to solve every unknown upfront, but it must not hide
unknowns as facts.

## Source priority

Use this order when researching external knowledge:

1. official documentation, official repository, release notes, API reference;
2. standards and government/industry guidance for security-sensitive decisions;
3. vendor documentation for provider-specific behavior;
4. reputable engineering references as secondary context;
5. community posts only as supporting evidence, not as the only source for a
   plan decision.

Record enough source detail that a future executor can re-check the claim.

## Required plan artifacts

For [L2] plans that depend on external knowledge, add one of these:

- a `Sources checked` section; or
- an `Evidence map` table; or
- explicit links from the relevant phase/decision rows.

Minimum evidence map shape:

| Claim / dependency | Source type | Freshness requirement | Close point |
|---|---|---|---|
| Semaphore static inventory supports web-edited inventory | official docs + local probe | re-check if API/UI version changes | Phase 1 |
| Ansible diff output may expose secrets | official docs | stable but verify when changing secret-bearing tasks | Phase 2 |

## Unknown classification

Classify unknowns as one of:

- `Known repo fact`
- `Verified external fact`
- `Assumption`
- `Needs web research before implementation`
- `Needs runtime probe`
- `Needs operator decision`

Each unknown must name when it closes:

```text
Unknown: exact Semaphore API payload for template launch
Close at: Phase 1 implementation
Method: official API docs + live API probe
If contradicted: update plan/add addendum before continuing
```

## When web research is required

Use current external research when the plan depends on:

- third-party tool behavior, API payloads, CLI flags, or licensing;
- current security best practice;
- OS/package/service configuration behavior;
- cloud/VPS provider behavior;
- Docker/image/runtime behavior;
- Ansible module/collection behavior;
- external product capabilities that determine whether to build or defer a
  custom component.

Local repo inspection remains sufficient for project-specific facts.

## References checked for this rule

- NIST SP 800-218 SSDF describes secure development practices as a common set of
  high-level practices integrated into the SDLC and focused on reducing
  vulnerabilities and their impact:
  https://csrc.nist.gov/pubs/sp/800/218/final
- Ansible documents check mode and diff mode as validation mechanisms, while
  warning diff mode can reveal sensitive information:
  https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_checkmode.html
- Docker documents secrets as runtime sensitive data that should not be stored
  in images or source control:
  https://docs.docker.com/engine/swarm/secrets/
- Semaphore UI documents the MVP-relevant surfaces: Inventory, Key Store, Tasks,
  and API:
  https://semaphoreui.com/docs/user-guide/inventory
  https://semaphoreui.com/docs/user-guide/key-store
  https://semaphoreui.com/docs/user-guide/tasks
  https://semaphoreui.com/docs/admin-guide/api
