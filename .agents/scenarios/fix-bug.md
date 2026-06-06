# Scenario: Fix Bug

1. Read `.agents/rules/coding-plan.md` before editing code or executable configuration, unless the fix is truly trivial hygiene.
2. Identify the failing behavior and the affected surface.
3. Check whether an investigation, changelog, or operational-truth doc already explains the failure mode.
4. Fix the root cause, not only the symptom, if the repo's current architecture supports it.
5. Add or run the narrowest test that proves the bug is fixed.
6. Sync docs if user-visible behavior changed.
