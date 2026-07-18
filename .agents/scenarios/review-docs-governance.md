# Scenario: Review Docs And Governance

Use this when the reviewed outcome is documentation, artifact lifecycle, or
agent/workflow governance. A plan proposing a feature, bugfix, refactor,
operation, or maintenance change inherits that proposed change as its primary
review type; use the relevant checks below as a bounded artifact check.

Review:

1. artifact responsibility and lifecycle: plan, review, investigation, stable
   design, decision, runbook, governance, test contract, or round evidence;
2. whether its directory and filename match
   `.agents/rules/file-naming.md`—use `docs/workstreams/` for new topic evidence
   and do not accept legacy `docs/reviews/` or `plan-*` as a default merely
   because the document relates to implementation;
3. audience, decision scope, authority, and relationship to current truth;
4. factual accuracy against code, active plans, TODO, and feature maps;
5. instruction routing, precedence, contradictions, and scope leakage;
6. referenced paths, commands, links, and status/approval semantics;
7. preservation of historical evidence versus current-state documentation;
8. whether the document can guide execution and verification without hidden
   assumptions.

Do not demand runtime tests for prose-only changes, but require path, command,
cross-reference, and diff checks appropriate to the touched surface.
Do not demand a new plan when an existing approved plan already covers the
phase; route probe evidence, accepted contracts, and procedures to their
canonical artifact locations instead.
