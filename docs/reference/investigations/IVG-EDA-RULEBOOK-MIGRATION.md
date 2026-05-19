# 技术调查报告 (Technical Investigation Report) - EDA Reactor Engine Selection: in-house vs `ansible-rulebook`

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-EDA-RULEBOOK-MIGRATION`
- **关联任务**: `feat-semaphore-cross-compare` Plan §4 WU-5a (Phase 2)
- **调查类型**: 架构探索 / 可行性研究
- **目标**: 回答四个核心问题：
  1. 继续自研 `controller/audit/reactor.py`（235 行 + 14 单测）vs 迁移到上游 `ansible-rulebook` 的总成本权衡
  2. 两者 event schema / rule DSL 是否兼容；迁移路径是否平滑
  3. 迁移后 ansispire 5-plane 模型如何调整（Reaction Plane 的执行器边界）
  4. 是否能保留现有 webhook action + per-rule cooldown 语义

## 2. 背景与问题描述 (Background)

### 2.1 初始观察
- 现有 reactor 是纯 stdlib Python 单进程（urllib + json + time + subprocess），通过 `tail -F`-like 模式读 `/var/log/semaphore/events.jsonl`，匹配 `extensions/eda/rules.json` 中的规则后调用 Semaphore HTTP API 触发 task。
- 上游 Ansible 官方有 **ansible-rulebook** 项目（`github.com/ansible/ansible-rulebook`，Apache-2.0，v1.3.0 / 2026-05-11，active），属 Event-Driven Ansible (EDA) 官方栈。
- IVG-SEMAPHORE-CROSS-COMPARE §5.A 列出"自研 reactor 偏离上游 EDA 路线"为 Tier 3 方向题，需 IVG 答复。

### 2.2 影响范围
- `controller/audit/reactor.py`（235 行）
- `extensions/eda/rules.json`（2 条规则）
- `extensions/eda/events.schema.json`（事件 schema）
- `controller/audit/docker-compose.yml`（reactor 容器：Alpine + Python，~80MB）
- 14 个 reactor 单测（`tests/unit/eda/test_*.py`）
- ansispire 5-plane 架构中的 **Reaction Plane**（执行器选型）

### 2.3 触发条件
- WU-5a 是 WU-7 决策点 "是否迁移到 ansible-rulebook" 的前置；未给结论则 WU-7 不能启动。

## 3. 调查过程 (Investigation Process)

### 3.1 假设 (Hypotheses)
1. **H-A**: ansible-rulebook 的 event source 能 tail-follow JSONL 文件 → 迁移可直接复用现有 events.jsonl 写入路径。
2. **H-B**: ansible-rulebook 的 condition DSL 表达力 ≥ 现有 `{key:val} + _contains` → 现有 2 条规则可机械翻译。
3. **H-C**: ansible-rulebook 的 throttle 语义 ≡ 现有 per-rule cooldown → 行为等价。
4. **H-D**: 迁移成本（运行时增量 + 容器改造 + 测试改造）相对当前 dev-stage 规模（2 条规则）显著偏高 → 不应现在迁移。

### 3.2 实验与验证 (Experiments)

#### 实验 1：source plugin 覆盖度
- **步骤**：检索 `event-driven-ansible` 仓库 `extensions/eda/plugins/event_source/` 目录
- **观察**：可用插件包括 `file_watch.py`（tail -F 语义）、`webhook.py`、`generic.py`、`journald.py`、`kafka.py`、`alertmanager.py`、`pg_listener.py`、`url_check.py`、`tick.py`、`range.py`、`aws_*` 等共 14 个
- **结论**：H-A 成立 — `ansible.eda.file_watch` 可直接替代 reactor.py 的 tail 循环

#### 实验 2：condition DSL 表达力
- **步骤**：阅读 [Conditions 官方文档](https://docs.ansible.com/projects/rulebook/en/latest/conditions.html)
- **观察**：支持 `==`、`!=`、`>`、`<`、`contains`、`not contains`、`in`、`is match()`（正则）、`is search()`、`and`/`or`/`not`、`is defined`、嵌套字段（`event.a.b.c`、`event.x[0]`）、多事件聚合（`events.m_0.x`）
- **结论**：H-B 成立 — 现有规则 `description_contains` 可写成 `event.payload.event.description contains "Disk Full"`；表达力反而是上游更强

#### 实验 3：throttle / cooldown 等价性
- **步骤**：阅读官方 throttle 章节
- **观察**：rulebook 提供 `throttle.once_within: 5 minutes` + 可选 `group_by_attributes`，语义为"窗口内首次触发后压制后续动作直到窗口结束"
- **结论**：H-C 成立 — 现有 `cooldown: 600`（秒）= `once_within: 10 minutes`，零损耗映射

#### 实验 4：迁移成本量化
- **步骤**：阅读 [Installation 文档](https://docs.ansible.com/projects/rulebook/en/latest/installation.html)
- **观察**：
  - Python ≥ 3.9 + **JDK 17+** + `jpy` Python ↔ Java 桥接（drools-jpy 是内部规则引擎）
  - 安装包：`pip install ansible-rulebook ansible ansible-runner`
  - 官方支持平台：Fedora / Ubuntu / macOS（不含 Alpine — jpy wheel 在 musl 上需源码编译）
  - 容器镜像增量预估：~300MB（JDK + jpy + Ansible 全套）vs 当前 Alpine + Python ~80MB
- **结论**：H-D 部分成立 — 运行时成本显著但可量化；container 必须从 Alpine 迁到 Ubuntu/Fedora

#### 实验 5：action 类型覆盖
- **步骤**：检索 rulebook 支持的内置 action 类型
- **观察**：`run_playbook` / `run_job_template`（AAP only）/ `run_module` / `post_event` / `set_fact` / `debug` / `print_event` / `shutdown`
- **结论**：现有 `semaphore_api` action（POST 到 `/api/project/N/tasks`）无原生对应；需用 `run_playbook` 调用包装 playbook 内的 `ansible.builtin.uri` 模块实现 — 多一层间接。webhook action 同理（`run_playbook` + `uri`）

## 4. 证据与日志 (Evidence & Logs)

### 4.1 现有 reactor 规则（rules.json）
```json
{
  "name": "Remediation: Disk Full",
  "cooldown": 600,
  "condition": {
    "object_type": "task",
    "description_contains": "Disk Full"
  },
  "actions": [
    {"type": "semaphore_api", "project_name": "ansispire",
     "template_name": "Auto Remediation: Disk Cleanup"}
  ]
}
```

### 4.2 等价 rulebook YAML（理论翻译）
```yaml
- name: ansispire EDA
  hosts: localhost
  sources:
    - ansible.eda.file_watch:
        path: /var/log/semaphore/events.jsonl
        recursive: false
  rules:
    - name: "Remediation: Disk Full"
      condition: >
        event.payload.event.object_type == "task" and
        event.payload.event.description contains "Disk Full"
      throttle:
        once_within: 10 minutes
      action:
        run_playbook:
          name: playbooks/trigger_semaphore_task.yml
          extra_vars:
            project_name: ansispire
            template_name: "Auto Remediation: Disk Cleanup"
```

伴随的 wrapper playbook（新增）：
```yaml
# playbooks/trigger_semaphore_task.yml
- hosts: localhost
  tasks:
    - ansible.builtin.uri:
        url: "{{ semaphore_url }}/api/project/.../tasks"
        method: POST
        headers: { Authorization: "Bearer {{ semaphore_token }}" }
        body_format: json
        body: { template_id: "{{ resolved_template_id }}" }
```

### 4.3 上游元数据
- **License**: Apache-2.0
- **Latest**: v1.3.0 (2026-05-11)
- **Maintenance**: 1275 commits on `main`, badge "Maintained? yes"
- **Runtime**: Python 3.9+ / JDK 17+ / jpy（drools 桥接）

## 5. 发现与分析 (Findings)

### 5.1 功能等价性
| 维度 | 现状（reactor.py）| ansible-rulebook | 等价? |
|---|---|---|---|
| Event 采集 | 自写 `tail -f` 循环 + JSON 解析 | `ansible.eda.file_watch` source | ✅ |
| 条件 DSL | `{key: val}` + `_contains` 后缀 | `event.x contains ...`、`is match()`、`and/or` | ✅ 上游更强 |
| 冷却 | per-rule `cooldown` (秒) | `throttle.once_within` (分/秒) | ✅ 直接映射 |
| 多事件聚合 | ❌ 不支持 | ✅ `events.m_0` / `events.m_1` 多事件相关 | ⬆️ |
| Hot-reload rules | ✅ 每 poll 重读 | ⚠ 通常需 SIGHUP / restart | ⬇️ |
| Action: Semaphore API | 原生（urllib POST）| 需 `run_playbook` + `uri` 间接 | ⚠ 间接 |
| Action: webhook | 原生（urllib POST）| 同上 — `run_playbook` + `uri` | ⚠ 间接 |
| Observability | 自写 stderr 时间戳日志 | 标准 ansible 日志格式 | 双向可改善 |
| 测试 fixture | 14 个 stdlib unittest，~500 行 | 需改写为 rulebook + 规则引擎 fixture | ⬇️ 重写成本 |

### 5.2 运行时成本
| 项目 | 当前 | 迁移后 | 增量 |
|---|---|---|---|
| 容器基础镜像 | `python:3.12-alpine` | Ubuntu/Fedora（jpy 限制） | base 变 |
| 镜像体积 | ~80MB（含 deps） | ~350-450MB（JDK + jpy + ansible + runner） | ×4-5 |
| 内存常驻 | ~30MB（单 Python 进程） | ~150-250MB（JVM 起步） | ×5-8 |
| 启动时间 | <1s | 3-8s（JVM 冷启动） | ×8 |
| 维护面 | 235 行 Python + 14 单测 | YAML 规则 + wrapper playbook + 上游版本跟进 | 不同形态 |

### 5.3 架构影响
- **Reaction Plane 边界**：当前 reactor 兼任 "rule matcher + action executor"，迁移后变为 "rulebook runner（matcher）→ wrapper playbook（executor）→ Semaphore API"，引入一跳。
- **5-plane 模型**：迁移属于 Reaction Plane 内部实现替换，不破坏其他平面契约（events.schema.json 不变；audit-sink/relay 不变；Semaphore API 调用不变）。
- **OSS 路线一致性**：迁移让 Reaction Plane 与上游 EDA 生态对齐，未来吸收 `alertmanager` / `kafka` / `journald` 等 source 时零开发成本（但当前规划没有此类需求）。

### 5.4 风险评估
- **不迁移的风险**：
  - 自写引擎能力上限低（无多事件聚合），未来规则增多时复杂度爆炸
  - 与上游 Ansible EDA 路线分叉，社区文档/示例无法直接利用
  - 维护负担在内部团队（235 行 + 14 单测的长期持有成本）
- **现在迁移的风险**：
  - 容器从 Alpine 切到 Ubuntu/Fedora，影响 `controller/audit/Dockerfile.reactor`（WU-2.6 计划中）
  - JVM 冷启动 + 内存 ×5-8，hub 资源预算（8c16g 工作站，远程 VPS 2c2g）需重评
  - 现有 14 单测全部重写（fixture 形态改变）
  - 当前仅 2 条规则，复杂度收益微弱（"鸡刀"）
  - 与 WU-2.2/2.3/2.4 reactor 鲁棒性改造冲突（同一文件大动）

## 6. 结论与建议 (Conclusion)

### 6.1 推荐方案
**结论**：**当前阶段不迁移**。维持自研 reactor，按 WU-2.2/2.3/2.4 计划做鲁棒性增强（mtime cache / cursor / structured log）。在以下任一**触发条件**达成后再启动迁移 IVG → 落地：

#### 触发条件（满足任一即应重启 IVG）
1. **规模触发**：`extensions/eda/rules.json` 中 enabled rules ≥ 5 条，**且**至少 1 条需要多事件聚合（如"5 分钟内连续 3 次 disk_full 事件"）
2. **集成触发**：明确需要吸收 `alertmanager` / `kafka` / `journald` 等任一非 jsonl 事件源
3. **平面拆分触发**：Reaction Plane 计划从 hub 单容器拆出独立部署（与 OSS Runner IVG-5b 决策耦合）
4. **运维触发**：自研 reactor 累计出现 3 次以上"规则匹配漏触发 / 误触发"P1/P2 issue（即引擎正确性出现规模化问题）

### 6.2 决策矩阵
| 因素 | 权重 | 自研 reactor 得分 | ansible-rulebook 得分 |
|---|---|---|---|
| 当前规则规模适配（2 条）| 高 | ✅ 5 | ⚠ 2 |
| 容器/资源预算适配 | 高 | ✅ 5 | ⚠ 2 |
| 未来扩展能力 | 中 | ⚠ 3 | ✅ 5 |
| OSS 生态对齐 | 中 | ⚠ 2 | ✅ 5 |
| 维护负担 | 中 | ⚠ 3 | ✅ 4 |
| 测试改造成本 | 中 | ✅ 5（已有）| ⚠ 2（需重写）|
| 与 WU-2 改造冲突 | 中 | ✅ 5 | ❌ 1 |
| **加权总分** | — | **~28** | **~21** |

→ 当前条件下自研明显占优；触发条件达成后权重会反转。

### 6.3 经验教训
- **不要为不存在的复杂度抽象**（W-R13 minimum-modification 精神延伸到引擎选型）。规则规模和复杂度是引擎选型的第一驱动力。
- **运行时成本是工程决策的硬约束**。即便迁移在功能上 100% 等价，~400MB 镜像 + JVM 内存占用对单 hub 部署模型是 5× 量级的成本变化。
- **保留切换通道**：现有 reactor 的 event-driven 设计（jsonl 文件 + JSON 事件）天然兼容未来 `file_watch` 源，迁移成本随时间不会指数增长。

### 6.4 对 WU-7 的输入
WU-7 关于 "是否迁移 ansible-rulebook" 的决策：**否（当前），但保留触发条件清单**。WU-7 启动前重读本 IVG §6.1 触发条件清单逐项核对。

## 7. 关联验证 (Linked Verification)
- **TSVS 引用**: N/A（IVG 不直接产出代码改动；触发条件达成后另起新 plan）
- **验证结果**: N/A（read-only investigation）
- **关联 IVG**:
  - [IVG-SEMAPHORE-CROSS-COMPARE](./IVG-SEMAPHORE-CROSS-COMPARE.md) §5.A 列出 reactor vs rulebook 为 Tier 3 方向题（本 IVG 答复）
  - [IVG-EXECUTION-PLANE-RUNNER](./IVG-EXECUTION-PLANE-RUNNER.md) — 平面拆分触发条件 #3 与之耦合
- **关联 Plan**: [feat-semaphore-cross-compare/plan-2026-05-17.md](../../reviews/feat-semaphore-cross-compare/plan-2026-05-17.md) §4 WU-5a
- **数据源**:
  - [ansible-rulebook GitHub](https://github.com/ansible/ansible-rulebook) — Apache-2.0, v1.3.0 (2026-05-11)
  - [event-driven-ansible source plugins](https://github.com/ansible/event-driven-ansible/tree/main/extensions/eda/plugins/event_source)
  - [Conditions documentation](https://docs.ansible.com/projects/rulebook/en/latest/conditions.html)
  - [Sources documentation](https://docs.ansible.com/projects/rulebook/en/latest/sources.html)
  - [Installation documentation](https://docs.ansible.com/projects/rulebook/en/latest/installation.html)

---
*Generated by Ansispire Investigation Engine — 2026-05-18*
