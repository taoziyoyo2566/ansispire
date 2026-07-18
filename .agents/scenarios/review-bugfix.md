# Scenario: Review Bugfix

Use this when the dominant intent is correcting an observed defect.

Review:

1. the symptom, reproduction, affected scope, and expected behavior;
2. evidence for the root cause and whether the fix reaches that cause;
3. failure modes, partial fixes, and adjacent regressions;
4. compatibility and recovery for already-affected state;
5. a regression test that fails before the fix and passes after it;
6. actual verification of the repaired workflow, not syntax alone.

Do not require a broad redesign when a narrow fix is complete and safe. Surface
larger design debt separately.
