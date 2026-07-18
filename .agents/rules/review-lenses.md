# Cross-Cutting Review Lenses

Apply these selectively after choosing one primary review scenario. They are
risk dimensions, not competing primary review types.

- **Security**: use when trust boundaries, credentials, authorization, exposed
  input, network access, or destructive capability changes.
- **Performance and scale**: use when latency, throughput, memory, storage,
  retries, concurrency, fleet size, or cost can materially change.
- **Compatibility and migration**: use when schemas, APIs, persisted state,
  filenames, variable names, supported versions, or operator payloads change.
- **Operability and recovery**: use when live state, remote systems, rollout,
  observability, rollback, or manual intervention matters.
- **Testability and evidence**: always check that the chosen acceptance carrier
  can observe the claimed effect; increase depth with change risk.

When the user explicitly requests a dedicated security, performance, or
compatibility audit, make that lens the report's focus while still identifying
the underlying change type. Do not silently expand an ordinary review into a
full specialist audit.
