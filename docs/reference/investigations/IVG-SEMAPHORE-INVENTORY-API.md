# 技术调查报告 (Technical Investigation Report) - Semaphore Inventory / Task API Contract

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-SEMAPHORE-INVENTORY-API`
- **关联任务**: `feat/target-architecture` Plan §4 Phase 1
- **调查类型**: API 契约调查 / 架构探索 / 设计校准
- **目标**:
  1. 明确 Semaphore Inventory CRUD 的公开契约，判断 CF Worker 应该按“整份 inventory 对象”还是“逐 host 子资源”建模
  2. 校准当前 owner branch 的真实状态，区分“已经落地的 repo 真相”和“设计文档里的待验证假设”
  3. 明确 Task API / Key Store 哪些字段已经足够进入 Phase 2 设计，哪些必须等待运行态实测

> **Runtime addendum (2026-06-06)**: The previously missing live probe has now run against Semaphore `v2.18.2`. It confirmed `static` inventory whole-object CRUD and task-level `environment` JSON as the runtime payload path for nested `vps_task`. Raw `extra_vars` remains unsupported as a Worker contract. Details are in §8.

## 2. 背景与问题描述 (Background)

### 2.1 初始观察
- `feat/target-architecture` 已删除本地 `vps_manager` 控制面，只保留 `playbooks/vps/` 生命周期内容。
- 当前 `controller/semaphore/bootstrap.yml` 仍创建 `type: "file"` inventory，指向 repo 内的 `hosts.ini` 路径，而不是把 inventory 内容放进 Semaphore DB。
- 目标架构设计文档仍把 `POST /api/project/{id}/tasks` 传 `extra_vars` 写成了既定事实，但本轮调查前并没有运行态证据支撑。
- `playbooks/vps/` 当前契约已经固定为：inventory 必须暴露 `vps_targets`，任务输入必须是顶层 `vps_task`。

### 2.2 影响范围
- `controller/semaphore/bootstrap.yml`
- `controller/semaphore/bootstrap_preflight.yml`
- `playbooks/vps/`
- `docs/reviews/feat-target-architecture/design-2026-05-26.md`
- 后续的 CF Worker / Wizard 接口契约

### 2.3 触发条件
- Plan §4 明确要求 Phase 1 先回答 Inventory / Task API 的真实契约，再进入 CF Worker 实现。

## 3. 调查过程 (Investigation Process)

### 3.1 假设 (Hypotheses)
1. **H-A**: 当前 owner branch 还没有真正切到 Semaphore `static` inventory，只是在文档层接受了这条方向。
2. **H-B**: Inventory 公开契约更像“整份 inventory 对象 CRUD”，而不是“每台 VPS 一条子资源”。
3. **H-C**: 设计文档里关于 Task API `extra_vars` 的说法，当前还不能直接当成实现前提。
4. **H-D**: 即便 Task API 额外参数机制最终可用，当前分支真正应该传递的也应是 `vps_task`，不是零散的 `vps_first_time_*` 顶层变量。

### 3.2 实验与验证 (Experiments)

#### 实验 1：审计当前分支的实际调用面
- **步骤**: 阅读 `controller/semaphore/bootstrap.yml`、`controller/semaphore/bootstrap_preflight.yml`、`playbooks/vps/README.md`、`playbooks/vps/onboard.yml`、设计文档 §3.4。
- **观察结果**:
  - bootstrap 仍调用 `POST /api/project/{id}/inventory`，但 body 里是 `type: "file"` + repo 内路径。
  - preflight full mode 只验证 project-scoped list 端点的顶层数组形状，没有覆盖 `GET /inventory/{id}`、`PUT /inventory/{id}`、Task launch 参数、static inventory blob。
  - `playbooks/vps/onboard.yml` 直接读取 `vps_task.bootstrap` / `vps_task.managed` / `vps_task.ssh`，而不是读取 `vps_first_time_*` 之类的顶层变量。
  - `playbooks/vps/README.md` 明确写了 `examples/*.yml` 是给 Semaphore Task API 的 `extra_vars` payload 参考。
- **结论**: H-A、H-D 成立。当前 repo 真相是“方向已接受，但 wiring 未完成”，且后续 payload 设计必须围绕 `vps_task`。

#### 实验 2：审阅 Semaphore 公开契约
- **步骤**: 审阅公开 API 参考 `https://api.semaphoreui.com/` 与官方 Terraform Provider 的 inventory 资源文档 `https://registry.terraform.io/providers/semaphoreui/semaphore/latest/docs/resources/project_inventory`。
- **观察结果**:
  - 公开契约中存在 project inventory 的 list / get-one / create / update / delete 路径。
  - `InventoryRequest` 公开字段至少包含 `name`、`project_id`、`inventory`、`type`，并可选 `ssh_key_id`、`repository_id`。
  - inventory 类型公开说明覆盖 `static`、`static-yaml`、`file`、`constructed`。
  - 本轮阅读到的公开 Task launch 契约快照里，`POST /api/project/{project_id}/tasks` 稳定暴露的是 `template_id`；没有看到与设计文档等价强度的 `extra_vars` 公开字段证明。
- **结论**: H-B 成立；H-C 目前不能判定为真，只能判定为“尚未被本轮公开证据证明”。

#### 实验 3：尝试补运行态实测
- **步骤**: 复用仓库内 preflight / compose harness 所需前置，检查 `.venv` 与 Docker daemon 可用性。
- **观察结果**:
  - 工作区不存在 `.venv/bin/ansible-playbook` 与 `.venv/bin/python3`。
  - Docker CLI 在，但 daemon socket 当前不可用：`/var/run/docker.sock` 链向 `~/.docker/run/docker.sock`，目标不存在。
- **结论**: 本轮无法在本机完成 live API 变异测试；运行态验证留到下一轮。

## 4. 证据与日志 (Evidence & Logs)

### 4.1 当前 bootstrap 仍使用 `file` inventory
```yaml
# controller/semaphore/bootstrap.yml
body:
  name: "{{ inventory_name }}"
  project_id: "{{ project_id | int }}"
  inventory: "{{ inventory_path_in_repo }}"
  type: "file"
  ssh_key_id: "{{ none_key_id | int }}"
```

### 4.2 当前 preflight 只覆盖 list 端点，不覆盖 item 级 inventory CRUD
```yaml
# controller/semaphore/bootstrap_preflight.yml
loop:
  - keys
  - repositories
  - inventory
  - environment
  - templates
```

### 4.3 生命周期 playbook 的真实输入契约是 `vps_task`
```yaml
# playbooks/vps/onboard.yml
- name: Onboard VPS into Ansispire management
  hosts: vps_targets
  vars:
    vps_bootstrap: "{{ vps_task.bootstrap }}"
    vps_managed: "{{ vps_task.managed }}"
    vps_ssh: "{{ vps_task.ssh }}"
```

### 4.4 本轮运行态验证被本地环境阻塞
```bash
$ ls -l .venv/bin/ansible-playbook .venv/bin/python3
ls: .venv/bin/ansible-playbook: No such file or directory
ls: .venv/bin/python3: No such file or directory

$ docker context ls
NAME              DESCRIPTION                               DOCKER ENDPOINT
default           Current DOCKER_HOST based configuration   unix:///var/run/docker.sock
desktop-linux *   Docker Desktop                            unix:///Users/ts-jinguo.sheng/.docker/run/docker.sock

$ ls -l /var/run/docker.sock /Users/ts-jinguo.sheng/.docker/run/docker.sock
ls: /Users/ts-jinguo.sheng/.docker/run/docker.sock: No such file or directory
lrwxr-xr-x /var/run/docker.sock -> /Users/ts-jinguo.sheng/.docker/run/docker.sock
```

## 5. 发现与分析 (Findings)

### 5.1 当前 owner branch 的“已证实真相”
| 主题 | 当前结论 | 置信度 | 说明 |
|---|---|---:|---|
| Inventory 模式 | 仍是 `file` inventory | 高 | 当前 bootstrap 没有落到 DB-backed `static` / `static-yaml` |
| Phase 1 覆盖度 | 还没真正做 item 级 inventory / task params 验证 | 高 | preflight 只看 list 端点形状 |
| 生命周期 payload | 应围绕顶层 `vps_task` | 高 | playbook 与 examples 已固定该契约 |
| Inventory group | 必须保留 `vps_targets` | 高 | `playbooks/vps/*` 已依赖这个分组 |

### 5.2 Inventory API 契约摘要
| 问题 | 当前结论 | 置信度 | 对 Phase 2/3 的含义 |
|---|---|---:|---|
| `POST /api/project/{id}/inventory` 的建模粒度是什么 | 更像“整份 inventory 对象 create/update” | 高 | CF Worker 应按读改写 blob / object 的方式设计 |
| 是否存在 per-host 子资源 | 本轮未见公开 per-host CRUD 入口 | 中高 | 不应先发明 host-level REST 语义 |
| Inventory 类型有哪些 | `static` / `static-yaml` / `file` / `constructed` | 高 | 现有 INI 风格资产优先对接 `static` |
| `GET /inventory/{id}` / `PUT /inventory/{id}` 是否存在 | 公开契约存在 | 中高 | 需要下一轮实测返回体与更新语义 |
| `GET /inventory/{id}` 是否返回完整 blob/content | 尚未运行态验证 | 中 | 这是 CF Worker CRUD 能否直接实现的关键门槛 |
| `PUT /inventory/{id}` 是 patch 还是 replace | 暂按 whole-object replace 处理 | 中 | Phase 2 前必须确认并发写边界 |

### 5.3 Key Store 最小 payload 结论
当前 repo 里已经有三类 AccessKey 创建样例，可作为下一轮实测前的最低可行输入参考：

| 类型 | 当前已观察到的最小 payload 形状 | 置信度 | 备注 |
|---|---|---:|---|
| `none` | `name` + `type=none` + `project_id` | 高 | 当前 bootstrap 已在主项目使用 |
| `ssh` | `name` + `type=ssh` + `project_id` + `ssh.{login,passphrase,private_key}` | 中高 | 当前注释表明空 `private_key` 在较早版本会被拒绝 |
| `login_password` | `name` + `type=login_password` + `project_id` + `login_password.{login,password}` | 中高 | 当前 demo project 已使用该形状 |

### 5.4 Task API 的当前判断
| 主题 | 当前结论 | 置信度 | 影响 |
|---|---|---:|---|
| 当前 repo 对 Task API 的使用 | 只 POST `{"template_id": <int>}` | 高 | `controller/audit/reactor.py` 已是现成证据 |
| 公开契约是否已证明 `extra_vars` | 否，本轮未找到同等强度的公开字段证明 | 中 | 设计文档不能继续把它写成已确认能力 |
| 后续 payload 应该长什么样 | 即便 Task API 有额外参数，目标也应是把 `vps_task` 送进去 | 高 | 不建议继续扩展 `vps_first_time_*` 顶层临时变量 |

### 5.5 对设计方向的直接影响
1. **Inventory 方向已经足够明确**：后续应围绕 `type: static`（INI blob）推进，而不是继续复制一套本地 inventory state。
2. **Task 参数方向仍需门控**：Wizard / Worker 不应在未实测前假定“Task API 直接吃 `extra_vars` 文本”。
3. **现有 design doc 需要校正**：首次上线参数的设计目标应该是构造 `vps_task.bootstrap`，而不是继续以 `vps_first_time_*` 为接口中心。
4. **preflight 必须扩展**：否则镜像升级或 API 漂移时，最关键的 item 级 inventory / task 参数回归没人看见。

## 6. 结论与建议 (Conclusion)

### 6.1 本轮可确认的结论
- Phase 1 的“静态契约调查”已经足够支持方向性决策：**回归 Semaphore 控制面时，Inventory 应按 `static` whole-blob CRUD 建模，生命周期参数应按 `vps_task` 建模。**
- 但 Phase 1 还**不能算完全闭环**，因为 `GET/PUT /inventory/{id}` 的具体返回体、whole-blob 更新语义，以及 Task launch 的运行参数承载方式还缺 live probe。

### 6.2 下一步建议
1. 起一个一次性的 Semaphore 实例，做最小 live probe：
   - `POST static inventory`
   - `GET /inventory/{id}`
   - `PUT /inventory/{id}`
   - `POST /tasks` with candidate runtime params
2. 将 probe 结果沉淀为可重复执行的契约门：
   - 扩展 `bootstrap_preflight.yml`，或
   - 新增专用 `probe_inventory_task_contract.*`
3. 在 live probe 之前，所有新设计都遵守两个硬约束：
   - inventory 以 `vps_targets` + INI blob 为目标
   - 任务 payload 以 `vps_task` 为目标

### 6.3 经验教训
1. 这条方向最危险的不是“没想清楚”，而是把旧设计假设写成当前事实。
2. 对第三方控制面的接入，必须把“公开契约”“本 repo 当前实现”“运行态实测”拆开写，否则后续 session 会误把设计草案当成事实来源。
3. 当前分支已经去掉了本地 `vps_manager`，所以后续任何补位方案都不应再把 host-level 本地状态文件引回来。

## 7. 关联验证 (Linked Verification)
- **TSVS 引用**: N/A（本轮为只读调查 + 文档校准）
- **验证结果**: 静态调查完成；2026-06-06 运行态探针补齐（见 §8）
- **后续门控**:
  - 把 `GET/PUT /api/project/{id}/inventory/{inventory_id}` 与 task-level `environment` payload 固化为可重复契约门
  - `static` vs `static-yaml` 在当前镜像版本下的行为差异

---

## 8. Runtime Addendum (2026-06-06)

### 8.1 Inventory CRUD

| Probe | Result | Impact |
|---|---|---|
| `GET /api/project/1/inventory/2` for `targets-managed` | `200`; full object returned; current inventory is `type: "file"` and `.inventory` is `inventory/hosts.ini` | Confirms current branch has not migrated production inventory to DB-backed static content. |
| `POST /api/project/1/inventory` with `type: "static"` | `201`; Semaphore persisted the INI blob verbatim | Confirms Worker can create static inventories. |
| `GET /api/project/1/inventory/3` | `200`; `.inventory` returned the stored INI blob | Confirms Worker can read the full blob for parse/mutate/serialize. |
| `PUT /api/project/1/inventory/3` | `204`; follow-up GET showed the replacement blob | Confirms whole-object update semantics; response has no body. |

### 8.2 Task Runtime Payload

| Probe | Result | Impact |
|---|---|---|
| `POST /api/project/1/tasks` with raw `extra_vars` | `201`, but task detail did not persist `extra_vars` and output did not prove Ansible received it | Do not use raw `extra_vars` as the Worker contract. |
| `POST /api/project/1/tasks` with `environment` JSON string | `201`; task detail preserved `environment`; Ansible debug output received nested `vps_task` | Use task-level `environment: JSON.stringify({ vps_task })` for onboard / modify / remove / audit runtime payloads. |

Minimal confirmed task body:

```json
{
  "template_id": 5,
  "environment": "{\"vps_task\":{\"probe\":true,\"source\":\"task-environment-field\"}}"
}
```

Observed Ansible output included:

```json
{
  "vps_task": {
    "probe": true,
    "source": "task-environment-field"
  }
}
```

### 8.3 Updated Conclusion

Phase 1 runtime probe is closed for the Worker-critical API contract:

- Inventory: `static` + whole-blob read-modify-write.
- Task payload: task-level `environment` JSON string carrying top-level `vps_task`.
- Remaining Phase 2 setup value: provision and record the real onboard template ID.

---
*Generated by Ansispire Investigation Engine | 2026-06-03 | branch: feat/target-architecture*
