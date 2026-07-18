# Scenario: Review Feature

Use this for a new capability, an extension of existing behavior, or an
architecture/design plan for such work.

For a plan, this scenario reviews the proposed system or product change. Apply
the bounded artifact checks routed by `review-change.md` without reclassifying
the plan as a docs/governance review.

Review in this order:

1. **Design goal**: state the intended outcome, users, boundaries, and non-goals.
2. **Problem fit**: identify the concrete problem and evidence; check whether
   the proposal addresses the root cause rather than only a symptom.
3. **Approach fit**: compare with current repo architecture and patterns. Check
   whether the framework/tool has a native or currently mainstream approach
   that is simpler or safer. Verify load-bearing external claims with current
   primary sources.
4. **Expected and actual effect**: assess observable behavior, operator impact,
   compatibility/migration, testability, and acceptance evidence. Label a
   plan-only effect as projected, not validated.
5. **Corrections and risks**: surface hidden assumptions, regressions, narrower
   alternatives, missing rollback/migration, and scope that should be deferred.
6. Only then review implementation details and tests.

Judge the feature against its stated goal; do not turn optional product or style
preferences into must-fix findings.
