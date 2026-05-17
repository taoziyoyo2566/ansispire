# Ansible 最佳实践审查报告 - feat/vps-manager-v2

| 项目 | 内容 |
|---|---|
| 审查日期 | 2026-05-16 |
| 审查范围 | 当前分支 `feat/vps-manager-v2` 相对 `dev` (`dc6083ccc0a9b8825842d0db6fa05f5bf40e6d8a`) 的修改 |
| 主要改动 | 删除 `plugins/vps_manager/`，新增 `plugins/vps_runner/`、`inventory/vps_runner/`、runner 文档与测试 |
| 结论 | **Changes requested**：方向正确，但有若干 Ansible 运维语义和安全边界需要在合并前收敛 |

## Findings

### P1 - `remove --cleanup-remote` 不能对称撤销 `onboard` 的 SSH 改动

`onboard.yml` 会直接修改主配置 `/etc/ssh/sshd_config`，把一组指令注释掉并转交给 `/etc/ssh/sshd_config.d/00-ansispire.conf` 管理：

- `plugins/vps_runner/playbooks/onboard.yml:397`
- `plugins/vps_runner/playbooks/onboard.yml:399`
- `plugins/vps_runner/playbooks/onboard.yml:401`
- `plugins/vps_runner/playbooks/onboard.yml:404`
- `plugins/vps_runner/playbooks/onboard.yml:416`

但 `remove.yml` 只删除两个 drop-in 并执行 `sshd -t`：

- `plugins/vps_runner/playbooks/remove.yml:20`
- `plugins/vps_runner/playbooks/remove.yml:25`
- `plugins/vps_runner/playbooks/remove.yml:29`
- `plugins/vps_runner/playbooks/remove.yml:36`

问题有两层：

1. 主配置里被注释的指令没有恢复，远端并不会回到 “distro-default sshd state”。
2. 删除 drop-in 后没有 reload/restart sshd 或 ssh socket，运行中的 sshd 仍可能继续使用旧配置，直到下一次服务重载。

这违反了 Ansible 配置管理里 “state=present/state=absent 可逆、变更触发 handler” 的基本期望。建议把 SSH 管理封装成对称的 role 或至少一个 task block：`present` 创建 drop-in、验证、notify reload；`absent` 删除 drop-in、恢复或避免修改主配置、验证、notify reload。若必须改主配置，应使用可追踪的 managed block 或明确备份恢复策略，不要只做广义 `replace`。

### P1 - Docker 期望被 inventory 和文档声明，但新 runner 没有实现

当前 dev host_vars 均声明 `features.docker: true`：

- `inventory/vps_runner/dev/host_vars/hk-d12.yml:24`
- `inventory/vps_runner/dev/host_vars/hk-d13.yml:24`
- `inventory/vps_runner/dev/host_vars/hk-u24.yml:24`
- `inventory/vps_runner/dev/host_vars/hy-hk-u24.yml:26`

运维文档也写明 onboard 会 “配置 UFW / fail2ban / docker”：

- `docs/operations/vps-runner.md:213`

但新 `plugins/vps_runner/playbooks/` 中只有一个未被引用的 `docker_daemon.json.j2` 模板，实际 playbook 没有 Docker 安装、daemon 配置、service enable 或 compose 部署逻辑。feature map 也承认旧插件的 `docker_host` / `deploy_compose` parity 尚未 port：

- `docs/reference/feature-map/vps-runner.md:48`
- `docs/reference/feature-map/vps-runner.md:68`
- `docs/reference/feature-map/vps-runner.md:128`

这会让 inventory 里的 desired state 无法收敛，是 Ansible 最忌讳的 “变量存在但无执行语义”。建议二选一：

- 将 Docker 从当前 cutover 的承诺、host_vars 示例和 docs 中移除，明确列为后续任务。
- 或新增 `docker_host` role/playbook，复用 `community.docker`/现有 role，并纳入 syntax/lint/Molecule 或最小 integration 覆盖。

### P1 - `suppress_env_files=True` 的安全声明过强，runner artifacts 仍写入完整进程环境

代码和文档将 `suppress_env_files=True` 描述为 “secrets not written to disk”：

- `plugins/vps_runner/vps_runner.py:239`
- `plugins/vps_runner/vps_runner.py:262`
- `docs/reference/feature-map/vps-runner.md:95`

实际运行后，`runtime/logs/vps_runner/<run_id>/command` 仍包含完整 `env` 字典，包括 `PATH`、`HOME`、会话变量、Ansible 变量等。本次观察到的样本：

- `runtime/logs/vps_runner/vps-runner-20260516T043703Z-dev-audit/command`

当前样本未显示凭据，但如果调用进程环境里存在 token、API key、vault 相关变量或临时密码，仍可能进入 artifact。`suppress_env_files=True` 只能避免写 `env/` 文件，不能被当成全量 artifact 脱敏。

建议：

- runner 调用前构造白名单环境，只传 `ANSIBLE_CONFIG`、`PATH`、必要 collection/role path 等最小集合。
- 文档改成 “避免写 env files，但 artifacts 仍需按敏感日志处理”。
- 如 artifact 要长期保留，应增加 command artifact 脱敏/清理策略，并把测试覆盖到这一点。

### P1 - 文档推荐的直接 CLI 入口对 `ansible-playbook` PATH 有隐性依赖

文档推荐入口是：

- `docs/operations/vps-runner.md:84`
- `docs/reference/feature-map/vps-runner.md:17`

核心调用只向 runner 传了 `ANSIBLE_CONFIG`，没有保证 `ansible-playbook` 所在目录进入 PATH：

- `plugins/vps_runner/vps_runner.py:253`
- `plugins/vps_runner/vps_runner.py:261`
- `plugins/vps_runner/vps_runner.py:269`

验证结果：

- `.venv/bin/pytest plugins/vps_runner/tests/ -m integration` 失败；artifact 中 rc=127，stdout 为 `The command was not found or was not executable: ansible-playbook.`
- `make test-vps-runner-integration` 通过，因为 Makefile 显式把 `.venv/bin` 放到了 PATH。

这说明当前实现依赖 Makefile 包装，而文档承诺的 `python -m plugins.vps_runner.cli ...` 并不自足。建议在 `run_playbook()` 中显式传递包含当前虚拟环境 bin 目录的 PATH，或将官方入口收敛为 Make target/console script，并让 integration test 覆盖直接 CLI 入口。

### P2 - onboard 使用本地 `ssh` 命令且关闭 host key 校验，绕过 Ansible 连接模型

`onboard.yml` 用 `delegate_to: localhost` 执行裸 `ssh` 来验证新端口和最终登录：

- `plugins/vps_runner/playbooks/onboard.yml:491`
- `plugins/vps_runner/playbooks/onboard.yml:502`
- `plugins/vps_runner/playbooks/onboard.yml:504`
- `plugins/vps_runner/playbooks/onboard.yml:578`
- `plugins/vps_runner/playbooks/onboard.yml:589`
- `plugins/vps_runner/playbooks/onboard.yml:591`

问题：

- 强制 `StrictHostKeyChecking=no` 和 `UserKnownHostsFile=/dev/null`，把主机身份校验从流程中移除了。
- 不复用 inventory 中的 `ansible_ssh_common_args`、ProxyJump、ControlPersist、connection plugin 等配置。
- 假设控制端一定有 OpenSSH CLI 和本地私钥路径，在 execution environment 或 CI runner 中不够可移植。

建议使用 Ansible 自身的连接语义完成验证：更新连接变量后使用 `wait_for_connection`/第二个 play，或在本地 `known_hosts` 中显式登记 host key 后再验证。至少应尊重 inventory 的 SSH 参数，并避免默认禁用 host key 校验。

### P2 - 新 inventory 仍把公共默认值和机器私有路径散落在每个 `host_vars`

多个 host_vars 重复了相同的安全策略、feature toggles、key path 和 metadata 结构：

- `inventory/vps_runner/dev/host_vars/hk-d12.yml:11`
- `inventory/vps_runner/dev/host_vars/hk-d12.yml:16`
- `inventory/vps_runner/dev/host_vars/hk-d12.yml:31`
- `inventory/vps_runner/dev/host_vars/hk-d12.yml:36`

Ansible 最佳实践通常是：

- `group_vars/vps_targets.yml` 或 `group_vars/all.yml` 放共同安全策略、默认 feature、默认 SSH key 变量。
- `host_vars/<alias>.yml` 只放每台机器真正不同的内容，如 `ansible_host`、managed user/port、status。
- 控制端私有路径尽量通过 `~`、环境变量 lookup 或 group var 抽象，而不是把 `/home/netcup/...` 写进每个 host_vars。

当前结构可用，但长期会放大 drift 风险，也降低其他操作员复现能力。建议在 cutover 后尽快引入 `inventory/vps_runner/dev/group_vars/vps_targets.yml`，把重复项上移。

### P2 - `onboard.yml` 过大，缺少 role/handler 边界

`plugins/vps_runner/playbooks/onboard.yml` 单文件承担了 package、user、sudoers、limits、swap、sysctl、fail2ban、UFW、sshd、systemd socket、验证等职责，接近 600 行。虽然 lint 和 syntax 都通过，但从 Ansible 可维护性看，这更像脚本化 playbook，而不是可复用 role。

具体影响：

- handler 语义不清：多处直接 `systemd state=reloaded/restarted`，而不是 template/package 变更 notify。
- 测试难拆分：无法对 SSH hardening、firewall、fail2ban 等独立做 Molecule/idempotence 断言。
- defaults/argument_specs 缺失：必填变量靠运行到中途才暴露。

建议把当前 playbook 拆成至少三个 role 或 task include：`vps_user`、`vps_ssh_hardening`、`vps_security_baseline`。短期可以先加 `pre_tasks assert` 覆盖 `vps_runner.identity_file`、`ansible_public_key`、`managed_user`、`managed_port`、OS family 等必填/支持边界。

## Positive Notes

- 相比旧 `vps_manager` 的 subprocess wrapper + custom state，迁移到 `ansible_runner.run()` 和标准 inventory 是正确方向。
- 新 playbooks 使用 FQCN，`ansible-lint --profile production` 对相关文件通过。
- `inventory=<abs path>` 避免了 `ansible.cfg` 默认 `inventory = inventory/prod` 的误打生产风险。
- `rotate_artifacts=10` 比默认无限保留更合理。
- `remove --yes`、`modify` 空变更拒绝、host_vars 缺失保护等 CLI guard 是有价值的。

## Verification

已执行检查：

| 命令 | 结果 |
|---|---|
| `git status --short --branch` | 审查开始时 clean，当前分支 `feat/vps-manager-v2` |
| `git diff --stat dev...HEAD` | 80 files changed, 5056 insertions, 3802 deletions |
| `make vps-runner-syntax` | 通过 |
| `env ANSIBLE_LOCAL_TEMP=/home/netcup/workspace/ansispire/.ansible/tmp ANSIBLE_REMOTE_TEMP=/tmp/ansispire-ansible-tmp .venv/bin/ansible-lint inventory/vps_runner plugins/vps_runner/playbooks` | 通过，0 failures |
| `.venv/bin/yamllint inventory/vps_runner` | 通过 |
| `.venv/bin/pytest plugins/vps_runner/tests/ -m 'not integration'` | 21 passed, 1 deselected |
| `.venv/bin/pytest plugins/vps_runner/tests/ -m integration` | 失败：直接 pytest 环境下 runner 找不到 `ansible-playbook` |
| `make test-vps-runner-integration` | 通过，1 passed |

说明：第一次直接运行 `ansible-lint` 时因沙箱默认临时目录指向 `/home/netcup/.ansible/tmp` 报只读文件系统；使用仓库内 `ANSIBLE_LOCAL_TEMP` 重跑后通过。

## Open Questions

- Docker 是否仍属于本次 `vps_runner` cutover 的合并范围？如果不是，应从当前 docs/host_vars 示例中移除或标成明确的 future work。
- `remove --cleanup-remote` 的目标到底是 “只删除 Ansispire drop-in” 还是 “恢复 distro/default SSH 状态”？当前实现和文档语义不一致。
- 是否允许把真实 dev VPS IP、用户和控制端绝对 key path 作为 git-tracked inventory 长期保存？如果要保留，建议至少把私有路径抽象到 group_vars 或本地未追踪 vars。

## Suggested Fix Order

1. 先修 `remove.yml` 与 SSH 配置可逆性，避免移除后远端处于非预期 SSH 状态。
2. 明确 Docker scope：删除承诺或补齐执行逻辑。
3. 收紧 runner 环境与 artifact 脱敏，修正 `suppress_env_files` 的文档表述。
4. 让直接 CLI 入口不依赖 Makefile PATH。
5. 拆分 inventory defaults 与 host-specific vars，再逐步 role 化 `onboard.yml`。
