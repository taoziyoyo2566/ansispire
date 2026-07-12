# 测试规格与验证说明书 (TSVS) - VPS Onboard → Managed-Channel Audit E2E

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-VPS-ONBOARD-E2E-001`
- **测试类型**: 功能测试 / 回环测试 (takeover + idempotency)
- **优先级**: 高
- **测试目的**: 验证 Saberu 接管闭环——从 bootstrap 通道对一台 VPS 执行 `VPS Onboard`（建 managed user/key/sudo、防火墙、fail2ban、把 SSH 切到非 22 managed 端口、关 bootstrap 端口），随后**改走 managed 通道重跑 `VPS Audit` 必须 `success` 且 `changed=0`**。核心断言:接管真实发生、且托管态幂等。附带验证 managed 登录校验**复用 Semaphore Key Store 钥匙**（无挂载私钥文件）。

## 2. 测试环境 (Environment)
- **控制面**: Semaphore v2.18.2（`ansispire-semaphore` 容器,uid 1001 跑任务),`ANSIBLE_CONFIG=/workspace/controller/semaphore/ansible.cfg`（vault-free）。
- **目标机**: 可恢复的 Debian 系 / RHEL 系 VPS,root@22 bootstrap 可达,root authorized_keys 已信任 fleet 公钥。
- **凭据**: fleet 私钥在 Semaphore Key Store（`vps-fleet-key`,passphrase 由 Semaphore 内部处理）;fleet 公钥用作 `vps_task.managed.authorized_keys[].public_key_content`。
- **网络**: 目标机可从容器网络出口直达;bootstrap 22 / managed 39222。

## 3. 软件包清单 (Software Stack)
| 软件名称 | 版本号 | 备注 |
| :--- | :--- | :--- |
| Ansible | core 2.21.0 (venv) / 镜像内 13.5.0 | 容器内跑 template |
| Semaphore | v2.18.2 | 控制面 |
| Docker | 29.3.1 | host `mail` |

## 4. 测试方法与步骤 (Methodology)
### 4.1 前置条件 (Prerequisites)
1. `make controller-bootstrap` 已建 `vps-fleet` / `vps-fleet-key` / `vps-onboard-env` / `VPS Onboard`（id 见 live）+ `vps-audit-env` / `VPS Audit`,两模板均绑定各自带 `ANSIBLE_CONFIG` 的 env。
2. 操作者在 Key Store 注入真实 fleet 私钥;`vps-onboard-env` 的 `public_key_content` = 真实 fleet 公钥;`vps-fleet` 填入目标机（bootstrap:`root@22`）。
3. 目标机 OS 为 Debian/RHEL 系且可恢复。

### 4.2 执行步骤 (Steps)
1. UI/API 触发 `VPS Onboard`（template）对 `[vps_targets]` 运行。`strategy: free` 使每台独立推进。
2. onboard 完成后,把 `vps-fleet` 改指 managed 通道:`ansible_user=<managed> ansible_port=<managed_port>`。
3. 触发 `VPS Audit`（template）对 managed 通道运行。
4. 观察两次任务的 `status` 与 PLAY RECAP。

### 4.3 关键实现点 (Assertions on mechanism)
- managed 登录校验(onboard.yml)走 **ansible 自身连接**,任务级 `ansible_user`/`ansible_port` 复用运行时 `--private-key`（Key Store 钥匙）——**无挂载 key 文件、无容器 uid 权限依赖**。
- onboard 为全 per-host,无跨主机顺序 → `strategy: free`,单台慢/hung 机不堵全队。

## 5. 预期结果 (Expected Results)
- [ ] `VPS Onboard` 任务 `status=success`;目标机 SSH 切到 managed 端口、bootstrap 端口关闭(tcp/22 closed、tcp/<managed> open)。
- [ ] managed 通道 `VPS Audit` 任务 `status=success`。
- [ ] 该次 audit **每台 `changed=0`、`failed=0`、`unreachable=0`**(托管态幂等)。
- [ ] 全程无挂载私钥文件、无 secret 材料落入 git。

## 6. 测试执行记录 (Actual Results)

**2026-07-11**（round12,commit `92df345` / `891ea21`）:

| 目标机 | OS | onboard | 切换后 tcp | managed 重审 |
| :--- | :--- | :--- | :--- | :--- |
| `test-vps-u24` | Ubuntu 24.04 | **success** (task 10) | 22 closed / 39222 open | **success, changed=0** (task 13) |
| `test-vps-d13` | Debian 13.5 | **success** (task 12) | 22 closed / 39222 open | **success, changed=0** (task 13) |
| `test-vps-r9` | Rocky 9 | **blocked** | — | — |

- **PASS(2/3)**:u24 + d13 满足全部预期断言(onboard success → 切 39222/关 22 → managed audit `success`+`changed=0`)。
- **r9 阻塞**:观察到的首个 blocker 是该 VPS 无法到达 EPEL 镜像，`dnf install fail2ban` hung；通过该点后仍需继续验证余下 RHEL 步骤。

## 7. 覆盖边界 / 待补 (Coverage gaps)
- **managed 审计幂等段已有自动化 carrier**:`make controller-vps-smoke`（`VPS Audit` 断言 `success` + 每台 `changed=0`;2026-07-11 对 u24+d13 PASS)。**onboard 接管段仍手动 + API**（接管是破坏性,不做重复冒烟）。
- RHEL 系全链路待 r9(或另一台 EPEL 可达的 RHEL)补齐。
- 未覆盖 offboard/还原(TASK-010)。
