# Claude 架构审查 — Round 7（控制面 PoC）

日期: 2026-04-14
执行者: Claude (Opus 4.6)
参照:
- [Round 6 架构方案](./claude-review-round-6-2026-04-14.md)
- [Review Iteration Charter](./review-iteration-charter.md)
- [CLAUDE.md](../../CLAUDE.md)

---

## 1. 原始目的

Round 6 提出"多服务器管理控制系统"的整体架构蓝图。Round 7 是该蓝图的**第一轮落地**：
引入**控制面（Controller）**，使 Ansible 从"脚本执行"升级为"有 API、有 Job、有项目同步"的受控系统。

## 2. 本轮关注范围

- 控制面选型（AWX vs Semaphore）
- 控制面本地部署（Docker Compose / k3s）
- 项目接入（控制面拉取本 repo 的 inventory/playbooks/roles）
- 一个最小 Job Template 示例（site.yml --check）
- 本地启动文档

## 3. 本轮不展开

- RBAC 细粒度策略（Round 8）
- 审计日志落盘 / SIEM 集成（Round 9）
- EDA / rulebook 接入（Round 10）
- 可观测性（Prometheus + Grafana）集成（Round 11）
- 高可用、DR、多租户（Round 12+）

## 4. 层级声明

**架构层**。新增子系统（控制平面），引入对外 API 边界。评审维度：控制面/数据面分离、身份边界、可观测接入点、与现有 repo 结构的兼容性。

## 5. 用户已给出的决策

| 项 | 决策 | 备注 |
|----|------|------|
| Q1 控制面 | 轻量开源优先 | **未绑定到 AWX——见第 6 节冲突** |
| Q2 部署 | Docker Compose 起步，可 k3s 学习 | 内存预算 **≈1 GB**（偶发超用可接受） |
| Q3 密钥 | ansible-vault | 外部 SM 示例保留为注释 |
| Q4 可观测性 | Prometheus + Grafana 最小栈 | Round 11 |
| Q5-Q7 | Claude 定 | 见下 |

**Claude 决策（Q5-Q7）**：

- Q5 教学/生产双示例：**仅单示例**（教学优先，简化）
- Q6 节奏：每轮 1-2 周，产出必须闭环
- Q7 Round 5 改动：**保持现状**作为地基

## 6. 关键冲突与备选：控制器选型

### AWX（官方开源控制面）
- 部署：仅支持 **k3s / k8s + AWX Operator**（Docker Compose 部署已于 2021 年弃用）
- 最小资源：**4-6 GB RAM + 2 CPU**（awx-web / awx-task / postgres / redis 四个 Pod）
- 生态最成熟，与 AAP 同源
- **不适配 1 GB 内存预算**

### Semaphore（社区轻量替代）
- 单进程 Go 二进制 + MySQL/Postgres/SQLite（可选 SQLite = 零外部依赖）
- 部署：**docker-compose 一条命令**
- 最小资源：**~200 MB RAM**
- 功能覆盖：project 同步、inventory、environment、job template、schedule、用户权限
- 社区活跃，开源 MIT 协议
- **非 AAP 同源**，迁移到 AAP 不是零摩擦

### Claude 推荐

**Round 7 用 Semaphore 起步**，理由：
1. 匹配 1 GB 内存预算
2. Docker Compose 一步启动，与用户 Docker 熟练度对齐
3. 所有控制面核心概念（project / inventory / template / job history）都能学到
4. 后续 Round（10+）如需 AAP 同源，可切到 k3s + AWX Operator 作为对比教学

**此项为唯一阻塞决策**。请确认采用 Semaphore，或要求改为 AWX on k3s（需接受 4-6 GB 内存占用）。

## 7. 任务分解（Round 7）

假设用户批准 Semaphore 路径：

| # | 任务 | 产出 |
|---|------|------|
| 1 | 新增 `controller/` 目录，放控制面资产 | 目录骨架 |
| 2 | `controller/semaphore/docker-compose.yml` | Semaphore + SQLite 最小部署 |
| 3 | `controller/semaphore/.env.example` | 管理员账号、端口、DB 路径样例 |
| 4 | `controller/semaphore/README.md` | 启动/停止/备份/重置步骤 |
| 5 | `controller/semaphore/bootstrap.yml` | 首次启动后的 API 配置脚本（创建 project/inventory/template） |
| 6 | `controller/README.md` | 控制面总览，对比 AWX 与 Semaphore，说明未来升级路径 |
| 7 | 根 `README.md` 新增"控制面"章节 | 指向 `controller/` |
| 8 | `Makefile` 新增 `controller-up` / `controller-down` 目标 | 一键启停 |
| 9 | 自检：docker compose up 成功、Web UI 可登录、一个 dry-run Job 能跑通 | 记录日志 |

**任务数 9**，按 CLAUDE.md R3 路线图先批原则，请用户在进入实施前确认此清单。

## 8. 与 Round 5 / Round 6 的关系

- **与 Round 5 地基的关系**：Round 5 已完成的 `ansible.cfg` / `execution-environment.yml` / `pyproject.toml` / inventory 结构可直接被 Semaphore 拉取，无需改动
- **与 Round 6 蓝图的关系**：本轮仅落地"控制平面"一项，其余 14 项差距矩阵保持未闭合状态，Round 8+ 逐项推进

## 9. 判断标准

- 是否让"控制平面 / 数据平面"概念落到可见系统？
- 是否引入了不必要复杂度（例如过早上 k8s）？
- 是否与现有 repo 结构解耦（controller/ 目录是否可独立启停）？
- 是否保留了向 AWX/AAP 升级的路径？

## 10. 自检点（实施后验证）

- [ ] `docker compose -f controller/semaphore/docker-compose.yml up -d` 无错误
- [ ] 浏览器访问控制面 Web UI 可登录
- [ ] 控制面能拉取本 repo 作为 project
- [ ] 能创建一个 inventory，指向 `inventory/production/hosts.yml`
- [ ] 能创建一个 job template 跑 `playbooks/site.yml --check`
- [ ] Job history 中可看到本次执行的 stdout
- [ ] `make controller-down` 可干净清理

## 11. 本轮不做

- 不接入外部 LDAP/OIDC（使用内置账号）
- 不配置 HTTPS（本地学习，HTTP 即可，下一轮或用户要求后加）
- 不实现审计日志外发
- 不接入 Prometheus 指标（Round 11）
- 不修改任何现有 role 或 playbook

## 12. 授权确认

请用户就以下明确授权：

- [ ] **Q1-b 选型**：采用 **Semaphore**（推荐） / AWX on k3s（需接受 4-6 GB RAM）
- [ ] 接受第 7 节的 9 项任务清单
- [ ] 接受"本轮不做"中列出的边界
- [ ] Round 7 完成后独立出 `round-7-change-log-2026-04-14.md`

**未获上述授权前，本方案仅为讨论稿，不进入任何实施。**
