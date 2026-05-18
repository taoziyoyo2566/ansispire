# 技术调查报告 (Technical Investigation Report) - OSS Runner Abstraction Feasibility

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-EXECUTION-PLANE-RUNNER`
- **关联任务**: `feat-semaphore-cross-compare` Plan §4 WU-5b (Phase 2)
- **调查类型**: 架构探索 / 可行性研究
- **目标**: 回答五个核心问题：
  1. Semaphore OSS Runner 实际部署形态（独立容器？独立 VPS？）
  2. Runner 注册 token 流如何 IaC 化（`bootstrap.yml` 是否能 mint runner token 并注入 runner 容器 env）
  3. 与现有 `[hub_local]` / `[hub_remote]` inventory 分组的关系
  4. Runner ↔ controller 网络拓扑（同 `controller-net`？跨网段？）
  5. 现有单容器执行模式何时迁出（触发条件）

## 2. 背景与问题描述 (Background)

### 2.1 初始观察
- 当前 ansispire 控制平面：单 `ansispire-semaphore` 容器同时承担 controller (UI + API + DB) **和** executor (跑 Ansible playbooks) 双重职责。
- 上游 Semaphore 提供 Runner 抽象：将 executor 从 controller 拆出独立部署，controller 仅负责调度与状态聚合。
- IVG-SEMAPHORE-CROSS-COMPARE §5.B 列 Runner 抽象为 OSS 可吸收方向（Tag-routing 是 Pro，基础 Runner 是 OSS）。

### 2.2 影响范围
- `controller/semaphore/docker-compose.yml`（controller 容器配置）
- `controller/semaphore/bootstrap.yml`（资源 IaC 化）
- `controller/runner/` (假定新增目录)
- `roles/ansispire_hub/`（部署链路扩展）
- `inventory/hosts.ini`（新分组 `[runner_*]`）
- `config/manifest.yml`（新端口 / 镜像 tag 引用）
- ansispire 5-plane 架构中的 **Data Plane / Execution boundary**

### 2.3 触发条件
- WU-5b 是 WU-7 决策点 "是否落 OSS Runner 抽象" 的前置；不答方向 WU-7 无法启动。

## 3. 调查过程 (Investigation Process)

### 3.1 假设 (Hypotheses)
1. **H-A**: OSS 版 Semaphore 完整支持 Runner 注册 + 任务调度（Tag-routing 是唯一 Pro 限制）。
2. **H-B**: Runner 注册 token 流可完全 IaC 化（在 `roles/ansispire_hub` 中扩展任务序列）。
3. **H-C**: Runner 与 controller 通过 HTTP/HTTPS 单向 outbound 通信，可跨网段 / 跨 VPS。
4. **H-D**: 当前单容器模型在 `[hub]` 单分组 + 2 条规则规模下无功能性必要拆分。

### 3.2 实验与验证 (Experiments)

#### 实验 1：Runner OSS 边界
- **步骤**：检索 [Runners 官方文档](https://semaphoreui.com/docs/administration-guide/runners/) + [Configuration 文档](https://semaphoreui.com/docs/administration-guide/configuration/)
- **观察**：
  - `semaphore runner setup` / `runner register` / `runner start` 三阶段 CLI 在 OSS 版本可用
  - `runner_registration_token` (config) / `SEMAPHORE_RUNNER_REGISTRATION_TOKEN` (env) — OSS
  - `use_remote_runner: true` / `SEMAPHORE_USE_REMOTE_RUNNER=True` — OSS
  - 公私钥对在 runner 注册时由 server 端自动生成与下发
  - 项目级"为 template 指定必须 tag X"才能跑 → 此特性标记 **(Pro)**
- **结论**：H-A 成立 — 基础 Runner 功能完全 OSS；只有 tag-routing 需 Pro

#### 实验 2：Runner 数据模型与协议
- **步骤**：读上游 `services/runners/types.go`（develop 分支）
- **观察**：
  ```go
  type RunnerRegistration struct {
    RegistrationToken string   `json:"registration_token"`
    Webhook           string   `json:"webhook,omitempty"`
    Name              string   `json:"name,omitempty"`
    Tags              []string `json:"tags,omitempty"`
    MaxParallelTasks  int      `json:"max_parallel_tasks"`
    Enabled           bool     `json:"enabled,omitempty"`
    PublicKey         *string  `json:"public_key,omitempty"`
    ProjectID         *int     `json:"project_id,omitempty"`
  }
  type RunnerState struct {
    CurrentJobs []JobState
    NewJobs     []JobData            `json:"new_jobs"`
    AccessKeys  map[int]db.AccessKey `json:"access_keys"`
    ClearCache  bool                 `json:"clear_cache,omitempty"`
  }
  ```
- **观察**：
  - 协议：runner **outbound poll** controller HTTP API → 拉取 `RunnerState`（含 `NewJobs` + `AccessKeys`）
  - 状态回报：runner POST `RunnerProgress`（含 `JobProgress` + `LogRecords`）回 controller
  - 加密：AccessKeys 用 RSA 公钥加密下发，runner 用私钥本地解密
  - Tags 字段存在于 OSS 数据模型 — 但仅作元数据，**调度匹配是 Pro**
- **结论**：H-C 成立 — 单向 outbound HTTP；runner 不需要 inbound 端口

#### 实验 3：注册 token 流程
- **步骤**：核对官方注册 CLI
- **观察**：
  ```bash
  # 方式 A: token in config file
  semaphore runner register --config /etc/semaphore/runner.json
  # 方式 B: stdin 注入
  echo "$REG_TOKEN" | semaphore runner register --stdin-registration-token --config /etc/semaphore/runner.json
  ```
- **结论**：H-B 成立 — token 是预共享密钥（pre-shared secret）；与现有 `.eda_token` 持久化模式同构，可复用 `state/.runner_token` 文件 + `ansible.builtin.uri` mint 流程

#### 实验 4：当前规模适配性
- **步骤**：检查现有 inventory + execution 形态
- **观察**：
  - `inventory/hosts.ini`：仅 `[hub_local]` + `[hub_remote]` 两个分组（控制平面部署目标）
  - `[hub]:children` = `[hub_local] + [hub_remote]`，但二选一（local OR remote），不并存
  - 真正的 *target fleet* (TASK-007) 尚未接入任何 OS 分支（RHEL / Alpine 是 fail-stub）
  - Execution 工作负载：bootstrap.yml 一次性导入 + 偶发 EDA 触发 remediation；并发任务实际为 1
- **结论**：H-D 成立 — 当前规模下拆分 controller / runner 无收益

## 4. 证据与日志 (Evidence & Logs)

### 4.1 现有控制平面网络
```yaml
# controller/semaphore/docker-compose.yml
networks:
  default: {}
  controller-net:
    external: true
    name: controller-net
# audit-relay / audit-sink / audit-reactor 都接入同一个 controller-net
```

### 4.2 假设的 Runner 拓扑（理论图）
```
┌────────────────────── workstation / hub VPS ──────────────────────┐
│                                                                    │
│  ┌─────────────┐    HTTP poll       ┌──────────────────┐           │
│  │ semaphore   │◄─────────────────► │ semaphore-runner │           │
│  │ (controller)│   /api/runners/... │  (executor)      │           │
│  └─────────────┘                    └──────────────────┘           │
│        ▲                                    ▲                      │
│        │ controller-net                     │ controller-net       │
│        └────────────────────┬───────────────┘                      │
│                             │                                      │
│              ┌──────────────┴──────────────┐                       │
│              │ audit-{sink,relay,reactor}  │                       │
│              └─────────────────────────────┘                       │
└────────────────────────────────────────────────────────────────────┘

# 跨 VPS 部署变体：
#   controller 留 hub；runner 部署到 target-fleet network
#   runner 需要出口能 reach https://hub.example/api/...
```

### 4.3 假设的 Runner compose 片段（理论）
```yaml
# controller/runner/docker-compose.yml （假设设计）
services:
  semaphore-runner:
    image: "semaphoreui/semaphore:${SEMAPHORE_IMAGE_TAG:-latest}"
    container_name: ansispire-semaphore-runner
    restart: unless-stopped
    command: ["semaphore", "runner", "start", "--config", "/etc/semaphore/runner.json"]
    environment:
      SEMAPHORE_RUNNER_API_URL: "http://semaphore:3000"
      SEMAPHORE_RUNNER_TOKEN_FILE: "/etc/semaphore/runner.token"
      SEMAPHORE_RUNNER_MAX_PARALLEL_TASKS: "2"
    volumes:
      - runner-config:/etc/semaphore
      - ../..:/workspace:ro
    networks:
      controller-net:
        aliases: [semaphore-runner]
volumes:
  runner-config:
networks:
  controller-net:
    external: true
    name: controller-net
```

### 4.4 假设的 IaC 注册流（理论 task 序列追加到 `roles/ansispire_hub/tasks/main.yml`）
```yaml
- name: API | Mint Runner Registration Token
  ansible.builtin.uri:
    url: "http://localhost:{{ ansispire_hub_port }}/api/runners"
    method: POST
    headers: { Authorization: "Bearer {{ ansispire_hub_eda_token }}" }
    body_format: json
    body: { name: "ansispire-runner-1", max_parallel_tasks: 2 }
    status_code: [200, 201]
  register: ansispire_hub_runner_token_out
  when: not (state_runner_token.stat.exists | default(false))

- name: Hub | Save Runner Token to State Dir
  ansible.builtin.copy:
    content: "{{ ansispire_hub_runner_token_out.json.registration_token }}"
    dest: "{{ ansispire_hub_state_dir }}/.runner_token"
    mode: "0600"
  when: not (state_runner_token.stat.exists | default(false))

- name: Hub | Start Runner Container
  community.docker.docker_compose_v2:
    project_src: "{{ ansispire_hub_base_dir }}/controller/runner"
    state: present
    wait: true
```

## 5. 发现与分析 (Findings)

### 5.1 可行性
| 维度 | 结论 |
|---|---|
| OSS 支持基础 Runner | ✅ 完全支持（仅 tag-routing 是 Pro）|
| Runner 镜像复用 | ✅ 同一 `semaphoreui/semaphore` 镜像，命令模式不同（`runner start` 而非默认 server 模式）|
| Token IaC 化 | ✅ 与现有 `.eda_token` 持久化范式同构 |
| 网络拓扑约束 | ⚠ runner 必须能 outbound HTTP reach controller |
| 复用 `controller-net` | ✅ 同 docker host 时直接 join；跨 VPS 时需暴露 controller HTTP 端口 |
| 与 `[hub_local]` / `[hub_remote]` 关系 | 不冲突 — runner 是新增分组（`[runner_*]`），与 hub 部署目标分组并列 |

### 5.2 拓扑选项
**Topology-A: 同主机双容器**（简单）
- controller + runner 都在同一 docker host
- 同 `controller-net`；runner 通过 `http://semaphore:3000` 访问 controller
- 适合：early adoption，验证 Runner 抽象
- 增量：1 个容器 + 注册流；workstation 8c16g 资源充足

**Topology-B: 跨 VPS 部署**（生产形态）
- controller 在 hub VPS；runner 在 target-fleet network 或独立 VPS
- runner outbound 需要 reach `https://hub.example/api/`（推荐 TLS）
- 适合：multi-tenant / 多 target fleet / 资源隔离
- 增量：TLS 反代 (A6 Tier 1) + 注册流 + 网络规则

**Topology-C: 单 runner 远端 + controller workstation**
- workstation 跑 controller（dev convenience）+ 远端 runner（真实执行环境）
- 适合：dev 阶段验证 runner 抽象的真实跨网行为
- 增量：workstation 暴露 controller 给 LAN（或反向：runner 暴露给 workstation）

### 5.3 与 ansispire 现状的耦合点
1. **manifest SSOT**：runner image tag 必须从 `config/manifest.yml` 派生（与 controller 同源），避免版本漂移
2. **EDA / API token 边界**：现有 EDA token 是 user token；Runner registration token 是另一类 secret，需新增 state file (`.runner_token`)
3. **bootstrap.yml 现状**：bootstrap 当前用 cookie 登录 + token mint；同方法可创建 runner 注册项
4. **AccessKey 加密**：runner 协议要求 controller 端启用 `SEMAPHORE_ACCESS_KEY_ENCRYPTION`（WU-3.1 计划中）；**强耦合** — Runner IaC 化前 WU-3 必须先 land

### 5.4 风险评估
- **现在引入的风险**：
  - 拓扑复杂度上升：1 个容器变 2 个，运维入口变多
  - 注册 token 是新一类 secret，需新的备份 / 恢复路径
  - bootstrap.yml 流程链路变长（mint → register → start → verify）
  - 与 WU-2 / WU-3 改造冲突（同步改 hub role）
  - 跨 VPS 拓扑下需要 TLS 反代，与 A6 (Tier 1 生产硬化) 强耦合
  - 当前 1 个 job/min 量级，runner pool 容量过剩
- **延迟引入的风险**：
  - 资源隔离边界缺失（"executor 拖死 controller" 单点）
  - 未来多 target fleet 时再迁移涉及历史 task 状态迁移问题（Pro tag-routing 是不可吸收能力，OSS 单 pool 模型够用）
  - 与 TASK-007 多 OS fleet 接入解耦延迟

## 6. 结论与建议 (Conclusion)

### 6.1 推荐方案
**结论**：**当前阶段不引入 Runner 抽象**。维持单容器 controller+executor 模型，直到以下任一**触发条件**达成：

#### 触发条件（满足任一即应重启 Runner 落地 plan）
1. **TASK-007 触发**：target fleet 接入 ≥ 2 个真实分组（如 `prod_alpine` + `prod_rhel`），且 controller 单容器的 job 并发已达瓶颈（>5 parallel jobs）
2. **资源隔离触发**：出现 1 次以上"远端 playbook 执行拖慢 controller UI 响应"的 P2 issue
3. **多租户触发**：开放给其他团队 self-service（A9，目前单租户假设）
4. **跨网拓扑触发**：业务上需要把 executor 放进 target network（合规 / 延迟 / 内网隔离原因）
5. **WU-3 完成触发**：`SEMAPHORE_ACCESS_KEY_ENCRYPTION` 已落地（强前置）

### 6.2 决策矩阵
| 因素 | 权重 | 维持单容器得分 | 引入 Runner 得分 |
|---|---|---|---|
| 当前 job 并发规模 (~1/min) | 高 | ✅ 5 | ⚠ 2 |
| 当前 fleet 规模（0 真实节点）| 高 | ✅ 5 | ⚠ 2 |
| 运维复杂度 | 中 | ✅ 4 | ⚠ 2 |
| 资源隔离 | 中 | ⚠ 2 | ✅ 5 |
| 跨网络部署能力 | 中 | ⚠ 2 | ✅ 5 |
| OSS 生态对齐 | 中 | ⚠ 3 | ✅ 5 |
| 与 WU-2 / WU-3 改造冲突 | 中 | ✅ 5 | ❌ 2 |
| **加权总分** | — | **~26** | **~23** |

→ 当前条件下维持单容器略优；触发条件达成后权重反转。

### 6.3 落地路径（Phase Gate 模型，**仅供未来参考**）
当触发条件达成时，建议按以下顺序落地（不是本 IVG 的产出）：

```
Gate 1: WU-3 已 merge (ACCESS_KEY_ENCRYPTION 持久化)
   ↓
Gate 2: controller manifest 加 SEMAPHORE_USE_REMOTE_RUNNER + token env
   ↓
Gate 3: 起 Topology-A (同主机双容器) 单 runner，IaC mint registration token
   ↓
Gate 4: bootstrap.yml 加 runner 资源注册 + smoke test (跑 1 个 template via runner)
   ↓
Gate 5: 决定 Topology-B 或 -C；引入 TLS 反代（A6）后切跨 VPS
   ↓
Gate 6: 扩展 inventory groups + manifest feature flag (`runner_pools.enabled`)
```

### 6.4 经验教训
- **抽象引入要看真实工作负载**。1 job/min 的执行规模下，引入 controller/executor 分离是过度设计（W-R13 minimum-modification 在抽象层的对应：minimum-abstraction）。
- **协议兼容性 ≠ 现在迁移收益**。OSS Runner 协议成熟、与现有 IaC 范式同构，迁移成本可控；但成本 = 等待 trigger 条件再付。
- **强耦合声明**：Runner 落地强依赖 WU-3 的 ACCESS_KEY_ENCRYPTION 持久化；如果将来同步推进，二者必须同 PR 或严格 WU-3 先行。
- **OSS 边界识别**：基础 Runner 是 OSS（够用），tag-routing 是 Pro（无法吸收）。规划时不要假设可以吸收 Pro 路由能力 — 单 pool 是 OSS 路径下的天花板。

### 6.5 对 WU-7 的输入
WU-7 关于 "是否落 OSS Runner 抽象" 的决策：**否（当前），但保留 5 项触发条件清单 + 4 阶段落地路径草案**。WU-7 启动前重读本 IVG §6.1 + §6.3。

## 7. 关联验证 (Linked Verification)
- **TSVS 引用**: N/A（IVG 不直接产出代码改动）
- **验证结果**: N/A（read-only investigation）
- **关联 IVG**:
  - [IVG-SEMAPHORE-CROSS-COMPARE](./IVG-SEMAPHORE-CROSS-COMPARE.md) §5.B 列 Runner 抽象为 Tier 3 方向题（本 IVG 答复）
  - [IVG-EDA-RULEBOOK-MIGRATION](./IVG-EDA-RULEBOOK-MIGRATION.md) — Reaction Plane 拆分触发条件 #3 与之耦合
- **关联 Plan**: [feat-semaphore-cross-compare/plan-2026-05-17.md](../../reviews/feat-semaphore-cross-compare/plan-2026-05-17.md) §4 WU-5b
- **数据源**:
  - [Semaphore Runners 文档](https://semaphoreui.com/docs/administration-guide/runners/)
  - [Semaphore Configuration 文档](https://semaphoreui.com/docs/administration-guide/configuration/)
  - 上游 `services/runners/types.go` (develop branch)
  - 上游 `services/runners/job_pool.go` (develop branch)

---
*Generated by Ansispire Investigation Engine — 2026-05-18*
