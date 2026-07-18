# Scenario: Review Maintenance

Use this for dependencies, build and CI configuration, test infrastructure,
developer tooling, or other maintenance whose main goal is not product behavior.

Review:

1. the maintenance gap, affected workflows, and why it matters now;
2. compatibility with supported environments and pinned versions;
3. reproducibility, caching, lock/freeze behavior, and supply-chain impact;
4. whether local and CI entry points remain aligned;
5. failure visibility, rollback, and contributor/operator disruption;
6. execution of the changed workflow on a clean or representative environment.

If maintenance intentionally changes runtime behavior, classify that portion as
a feature or bugfix instead of hiding it under tooling scope.
