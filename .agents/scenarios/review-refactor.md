# Scenario: Review Refactor

Use this when internal structure changes while externally observable behavior is
intended to remain stable.

Review:

1. the behavior baseline that must remain unchanged;
2. the structural problem and measurable benefit of the refactor;
3. whether the new abstraction reduces duplication or merely moves it;
4. API, data, configuration, ordering, and side-effect equivalence;
5. migration and rollback for renamed or relocated surfaces;
6. equivalence/regression evidence plus tests for the new seams.

Treat an unacknowledged behavior change as a feature or bugfix scope change, not
as a harmless refactor detail.
