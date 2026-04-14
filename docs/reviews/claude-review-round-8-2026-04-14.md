# Claude 架构审查 — Round 8（IAM + 凭证集中 + 轻量审计）

**状态**: 已归档，待后续授权（用户 2026-04-14 决定暂缓实施）
**恢复方式**: 用户确认"继续 Round 8"后，回到第 14 节授权清单，逐项裁决

日期: 2026-04-14
执行者: Claude (Opus 4.6)
参照:
- [Round 7 方案 / 变更](./claude-review-round-7-2026-04-14.md) / [change log](./round-7-change-log-2026-04-14.md)
- [Round 6 架构方案](./claude-review-round-6-2026-04-14.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## 1. 原始目的

Round 7 引入了控制平面（Semaphore）。Round 8 让控制平面具备**身份与凭证能力**：
- 从"只有一个全权 admin"升级为"用户/团队/项目角色分层"
- 把散落在文件系统的 SSH key / vault 密码集中管理
- 所有管理动作有**审计痕迹**（谁、什么时候、做了什么）

这是把 Ansible 从"脚本模式"真正变成"管控系统"的关键一步。

## 2. Round 6 路线图对齐与范围调整

Round 6 Round 8 原文（基于 AWX 假设）：
> RBAC + SSO (OIDC) + 审计日志导出到 Loki

**本轮调整（因 Round 7 改用 Semaphore）**：
- RBAC：保留（Semaphore 内置 User / Team / Project role 能力充分）
- SSO (OIDC)：**推迟**。需要 Keycloak/Authentik（~512 MB RAM），与 1 GB 预算冲突；且单人学习场景 SSO 价值有限
- 审计到 Loki：**推迟到 Round 9**。Round 9 才部署可观测性栈；本轮改为"本地 JSON 落盘 + 轮转"作为地基
- **新增**：凭证集中（SSH key / vault password）——这是 Round 6 原本埋在 Round 10 的内容，但实际属于 IAM 范畴，应在 Round 8 做

调整理由：**控制器选型变化导致子主题边界变化**，把"最该在 IAM 轮做"的事都收进来，把"依赖其他能力"的推迟到对应轮。

## 3. 本轮关注范围

- 子主题 A：**RBAC 示例** — 创建 2 个用户、2 个 team、演示 project role 绑定
- 子主题 B：**凭证集中** — SSH key 和 vault password 从宿主文件迁入 Semaphore keystore
- 子主题 C：**轻量审计** — Semaphore 事件 webhook 接收器（宿主侧 JSON 落盘 + logrotate 配置）
- 子主题 D：**bootstrap.yml 扩展** — 增加 team / user / key 的幂等创建

## 4. 本轮不展开

- ❌ OIDC / SSO（推迟至 Round 11 或用户升级到有可观测性栈后再评估）
- ❌ Loki / ELK 集中日志（Round 9 可观测性栈）
- ❌ LDAP 集成
- ❌ HashiCorp Vault 后端（Round 10）
- ❌ 多租户隔离（Round 12）
- ❌ 密钥轮换自动化（Round 10）

## 5. 层级声明

**架构层**。引入身份模型与凭证边界，改变了系统的信任关系。评审维度：
- 最小权限原则（RBAC 角色默认拒绝）
- 凭证出入边界（谁能导入、谁能使用、谁能导出）
- 审计可追溯性（事件覆盖率、时间戳来源、防篡改）
- 与 Round 7 解耦（控制面启停不破坏身份数据）

## 6. 当前状态评估

| 维度 | 现状（Round 7 后）| 差距 |
|------|-------------------|------|
| 身份 | 单个 admin 账号 | 无角色分层、无 team 组织 |
| 凭证 | SSH key 在 `~/.ssh/`、vault 密码在 `.vault_pass` | 凭证和代码/执行环境耦合；切换用户无法复用 |
| 审计 | `docker logs` 输出 Semaphore 事件 | 无结构化、容器重建会丢、无法查询 |
| 边界 | admin 可任意创建 project / 触发 job | 无"只能读不能写"的角色示例 |

## 7. 目标架构（Round 8 后）

```
┌──────────────────────────────────────────────────────────┐
│  Semaphore 控制面（已有，Round 7）                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │  Users   │  │  Teams   │  │  Project Roles     │    │
│  │  admin   │  │ platform │  │  owner / manager / │    │
│  │  dev1    │→ │   dev    │→ │  task_runner / guest│   │
│  │  dev2    │  │          │  │                    │    │
│  └──────────┘  └──────────┘  └────────────────────┘    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Keystore                                       │    │
│  │  - ssh_lab_key (SSH private key)                │    │
│  │  - vault_prod_password (login/password type)    │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│                         ▼ 事件流                          │
└──────────────────────────┼───────────────────────────────┘
                           │ (webhook POST)
                           ▼
                ┌──────────────────────┐
                │ audit-sink 容器      │
                │ (轻量 Python/caddy)  │
                │                      │
                │ /var/log/semaphore/  │
                │   events.jsonl       │
                │ + logrotate         │
                └──────────────────────┘
```

## 8. 任务分解（10 项，估中等规模）

| # | 任务 | 产出 |
|---|------|------|
| 1 | 设计 4 个角色的权限矩阵（owner / manager / task_runner / guest）| `controller/rbac/role-matrix.md` |
| 2 | bootstrap 扩展：创建 2 个 team（platform / dev） | `bootstrap.yml` 增量 |
| 3 | bootstrap 扩展：创建 3 个示例用户并分配 team | `bootstrap.yml` 增量 |
| 4 | bootstrap 扩展：创建 3 个 project role 绑定示例 | `bootstrap.yml` 增量 |
| 5 | SSH key 导入流程文档 + bootstrap 自动导入示例 | `controller/rbac/README.md`、bootstrap 增量 |
| 6 | vault password 作为 Semaphore "login_password" 凭证 | bootstrap 增量 |
| 7 | 审计 sink 容器 | `controller/audit/docker-compose.yml`（追加到主 compose 或独立） |
| 8 | 审计 sink 代码（接收 webhook，追加到 jsonl） | `controller/audit/sink.py`（最小 Flask/FastAPI） |
| 9 | Makefile 新增 `controller-audit-tail` 目标 | `Makefile` 增量 |
| 10 | Round 8 自检：手动触发 3 种角色行为、验证 audit 日志、验证 key 使用 | `round-8-change-log-*.md` |

**任务数 10**，按 R3 路线图先批原则，**请用户过目此清单再进入实施**。

## 9. 关键决策点

| # | 决策 | 选项 | Claude 建议 |
|---|------|------|-------------|
| D1 | 审计 sink 形态 | (a) Python Flask 容器 / (b) Caddy + access log / (c) Semaphore webhook → 本地文件（无 sink） | **(a) Python Flask**：可解析事件结构、未来可加过滤，~30MB RAM |
| D2 | 示例用户密码 | (a) 强随机生成写入 `controller/rbac/users.yml`（gitignore）/ (b) 统一 demo 弱密码写文档 | **(a) 随机生成**：贴近生产习惯，用户可自主导出 |
| D3 | vault_pass 是否真导入 | (a) 导入真实 `.vault_pass` / (b) 只做机制演示（创建占位凭证） | **(b) 占位**：本地演示期不要把真 vault 密码写入 Semaphore 状态，等用户明确后再真导入 |
| D4 | 审计 jsonl 保留 | (a) 持久化 volume / (b) 仅容器运行期保留 | **(a) 持久化**，logrotate 保留 7 天 |
| D5 | RBAC 作用范围 | (a) 仅本 repo 的 project / (b) 创建独立示例 project `round8-rbac-demo` | **(b) 独立示例**：避免在主 project 上做权限实验影响 Round 7 的 dry-run template |

## 10. 判断标准

- 是否演示了"最小权限"原则（至少有一个 guest 角色只能看不能跑）？
- 凭证是否真的与代码 repo 解耦（删除宿主 `~/.ssh/id_rsa` 后 job 仍能跑）？
- 审计日志是否结构化、可被 grep/jq 查询？
- 现有 Round 7 的 dry-run template 是否仍能跑通？

## 11. 自检点（实施后验证）

- [ ] `make controller-bootstrap` 幂等（运行两次不产生副本）
- [ ] 用 `dev1` 登录后，**不能**创建新 project（guest / task_runner 权限生效）
- [ ] 用 `dev2` 登录后，**能**触发 round7 template 但**不能**编辑
- [ ] SSH key 从 Semaphore keystore 引用后，job 能成功 SSH（用 localhost + 受管 container）
- [ ] 审计 jsonl 文件包含登录/project 创建/job 触发事件
- [ ] `jq '.event' events.jsonl | sort | uniq -c` 可统计事件类型
- [ ] `docker stats` 总内存 < 300 MB（Semaphore ~ 7 MB + audit sink ~ 30 MB + 余量）

## 12. 成本预算

- 预估：**中（~2 h）**
- 拆分可能：若时间紧，可把子主题 C（审计 sink）拆到 Round 8.5 单独一轮
- 风险：Semaphore RBAC API 文档不如 AWX 完整，可能需要读源码印证字段

## 13. 与既有改动的关系

- **不修改** Round 7 的 docker-compose.yml（audit sink 另起一个 compose 或独立服务）
- **扩展** bootstrap.yml（向下兼容，已创建资源不会重建）
- **扩展** Makefile（新增目标，不改已有）
- **新增** `controller/rbac/`、`controller/audit/` 子目录

## 14. 授权确认

请用户就以下明确授权：

- [ ] 接受第 2 节的**范围调整**（OIDC/Loki 推迟，凭证集中前置到 Round 8）
- [ ] 接受第 8 节的 **10 项任务清单**
- [ ] 对第 9 节 5 个决策点给出裁决（可全部采纳 Claude 建议）
- [ ] 接受第 4 节的**本轮不做**边界
- [ ] Round 8 完成后独立出 `round-8-change-log-2026-04-14.md`

**未获上述授权前，本方案仅为讨论稿，不进入任何实施。**
（遵循 CLAUDE.md R1 方案先行 + R3 路线图先批原则）
