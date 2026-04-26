# Test Infrastructure Summary (feat/test-infra)

## 1. Multi-Node Simulation Matrix
To ensure cross-platform consistency, we use a tiered Docker-based matrix:
- **ubuntu22-node**: Primary Tier 1 platform (LTS).
- **ubuntu20-node**: Legacy LTS compatibility. Uses `common_ufw_enabled: false` to bypass Docker-specific ip6tables issues.
- **debian12-node**: Upstream consistency check.

## 2. Environmental Awareness Logic
The system is designed to "sense" its environment rather than failing:
- **IPv6 Detection**: `roles/common` checks `/proc/net/if_inet6` before configuring UFW.
- **Service Existence**: SSH tasks use `stat` on `sshd_config` to avoid failing in minimal containers.
- **Dependency Auto-Healing**: Missing system services like `cron` are explicitly installed to satisfy role handlers.

## 3. Configuration Best Practices
- **ansible.cfg**: Uses `result_format = yaml` (ansible-core 2.13+) and suppresses collection/localhost warnings.
- **molecule.yml**: Uses `host_vars` for granular platform overrides, ensuring high precedence.
- **verify.yml**: Assertions are wrapped in `when` conditions to match the platform's specific configuration.

## 4. Test Documentation Standards (TSVS)
Starting from April 2026, all functional and loopback tests must follow the **TSVS** template:
- **Location**: `docs/test-specs/`
- **Template**: `docs/test-specs/TEMPLATE.md`
- **Requirements**: Must include Software Stack versions, specific Methodology, and evidence-based Actual Results.

## 5. Key Learnings (The "Don't Repeat" List)
1. Do NOT symlink `ansible` to other tools in `bootstrap.sh`; let pip manage the entrypoints.
2. Molecule does NOT inherit project-level `PYTHONPATH`. Explicitly map plugins in `molecule.yml`.
3. In Docker, RHEL 9 (Rocky/Alma) PAM management is often restricted by the host kernel; use standard VM tests for heavy security validation.
