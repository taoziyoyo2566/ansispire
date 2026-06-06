# Operational Quirks

Use `docs/governance/operational-truths.md` as the canonical source.

- The pinned baseline is Ansible-Core 2.20.5.
- Test containers often lack services or files you would expect on real hosts; code should sense environment before mutating it.
- `become: false` is required on playbooks writing to the control-node filesystem.
- Avoid `:latest` in pinned manifests.
- Long-distance or high-latency operations favor task consolidation over many small remote mutations.
