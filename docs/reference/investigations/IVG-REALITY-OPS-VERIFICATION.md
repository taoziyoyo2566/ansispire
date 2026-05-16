# 技术调查报告 — Reality-Ops 迁移方案独立复核

## 1. 调查概览 (Overview)
- **调查 ID**: `IVG-REALITY-OPS-VERIFICATION`
- **关联输入**: 4 份 Gemini 产物（2 份分析/迁移方案 md + `scripts/manage_reality_users.py` + `inventory/targets/users/testuser.yml`），已在本次 round 全部丢弃；本 IVG 完成对它们的复核与论据封存，原文不再保留。Gemini 关键断言已在 §5.1 表中逐条引用。
- **调查类型**: 可行性研究 + 同行复核（second-opinion）
- **目标**: 验证 Gemini 关于 `taoziyoyo2566/reality-ops@feat/tag-acl-routing` 项目的功能解构与缺陷诊断是否真实可靠，识别遗漏与误读，给出可落地的修订方案。
- **复核范围**: 仓库 commit `1fb10f0`（feat/tag-acl-routing 分支当前 HEAD）。

## 2. 背景与问题描述 (Background)
- **初始观察**: Gemini 给出 5 章「积木」解构 + 5 章「缺陷-改进」方案，但产出和方案自相矛盾（方案要求统一 YAML + Vault 加密，落地脚本却继续写 JSON-in-`.yml` 且密钥明文）。
- **影响范围**: 任何后续基于该方案的迁移工作都会继承误判；若以「Gemini 已盘点完毕」为前提进入实施阶段，会漏掉 `monitor/`、`audit.yml`、`reset.yml`、`acl_matrix`、`generate_subs_gist.py` 等核心子系统。
- **触发条件**: 用户对 Gemini 方案不信任，要求 second-opinion。

## 3. 调查过程 (Investigation Process)

### 3.1 假设
1. **H1**: Gemini 的「5 个积木」覆盖完整 → 由此可判断迁移工作量。
2. **H2**: Gemini 列出的 5 个缺陷与改进方案是基于真实代码的诊断。
3. **H3**: 已落地的 `manage_reality_users.py` + `testuser.yml` 实现了方案宣称的改进。

### 3.2 实验与验证
- **步骤 1**: `git clone --depth 1 --branch feat/tag-acl-routing https://github.com/taoziyoyo2566/reality-ops.git /tmp/reality-ops`，遍历全部文件清单（72 个文件），统计行数。
- **步骤 2**: 通读 `README.md`、`deploy.yml`、`reset.yml`、`audit.yml`、`monitor.yml`、`roles/reality_{single,multi}/`、`roles/monitor/`、`group_vars/all/main.yml`、`generate_user.py`（709 行）、若干 `host_vars/*.yml` 与 `users/*.yml`。
- **步骤 3**: 把 Gemini 的逐条断言映射回上述文件，逐一打分（见 §5 表）。
- **步骤 4**: 对比 `scripts/manage_reality_users.py`（240 行）与上游 `generate_user.py`（709 行），盘点丢失能力。

## 4. 证据与日志 (Evidence)

### 4.1 仓库真实拓扑（Gemini 完全没提到的子系统加粗）
```
deploy.yml              # 总入口，含 ACL 矩阵预过滤 + 子角色调度
**reset.yml**           # 469 行：清理容器/数据/订阅缓存，含 reset_target_hosts / reset_subs_only / 二次确认
**audit.yml**           # 65 行：聚合各节点 access.log 做用户-IP 去重审计
**monitor.yml**         # 旧入口（README 标注为"遗留"，但仍存在）
**generate_subs_gist.py** # 订阅聚合 → 推送 GitHub Gist
roles/reality_single/   # 单容器 + 多端口 inbound（Gemini 完全没提单实例模式）
roles/reality_multi/    # 容器-per-用户（Gemini 描述的就是这一种）
**roles/monitor/**      # FastAPI 服务端 + agent，每分钟上报流量
**docker-build/**       # 自建 xray 镜像（alpine + xray binary）
**group_vars/all/main.yml**  # 含 acl_matrix（层级 free→cm→basic→normal→premium + 特性组）
**group_vars/all/vault.yml** # vault 加密的 token / socks5 凭据
**host_vars/*.yml × 13** # 节点级覆盖 reality_mode / monitor_enabled / socks5
**inventory.ini**       # 节点组定义（free/basic/normal/premium/cmi/special），是 acl_matrix 的另一半
users/*.yml × 29        # JSON-in-.yml 用户文件（含明文 X25519 私钥，已 push 到公开 repo）
```

Gemini 5 章对应的覆盖率：~40%。

### 4.2 关键代码事实
- `deploy.yml:28-55` — ACL 过滤逻辑真正的位置。机制是「节点 inventory 组 → `acl_matrix` 展开放行标签 → 与用户 `groups` 取交集，或命中 `hosts` 直连」。Gemini 把这个机制压缩成"标签驱动的 ACL 路由"，掩盖了 `acl_matrix`（层级矩阵）这个核心数据结构。
- `roles/reality_multi/templates/config.json.j2:1-128` — 全文 **2 个** `{% if %}` 条件（socks5 出口块 + 内部凭据块），不存在 Gemini 所谓"大量 if/else 逻辑"。
- `roles/reality_multi/tasks/main.yml:128` — `/tmp/reality_build` 路径硬编码，**确认**。
- `roles/reality_multi/tasks/main.yml:194-205` — 对远端 rsync 的检查及失败提示，**确认**依赖。
- `roles/reality_single/templates/config.json.j2:1-107` — 与 multi 模式完全不同的拼装策略（单容器多 inbound），Gemini 未提及。
- `group_vars/all/main.yml:6` — `reality_server_names: ["www.apple.com", ...]` —— 不是 Gemini 说的 Microsoft。
- `generate_user.py:398-435` — `reexec_in_docker()` 35 行 `docker run --rm -v <repo>:/app …`，**bind-mount 重执行**，不是「Docker-in-Docker」。
- `users/lin_isp.yml` 等 29 个文件 —— 真实用户的 `private_key` 明文，已推到公开仓库。这是上游一个**实际严重得多**的安全问题，Gemini 把它降级成"不符合 Ansispire 安全标准"的措辞。

### 4.3 Gemini 已落地产物的回归点
- `scripts/manage_reality_users.py`（240 行）相对上游 `generate_user.py`（709 行）丢失：
  - `delete` 子命令（plan 移植清单中标注存在，但实际未实现）
  - `update` 子命令（plan 移植清单同上）
  - `--force / --include-json / --details / --wide / list-of-records` 模式
  - `--docker` 二次执行链路（保留了常量 `DOCKER_SENTINEL_ENV` 与 `OPTIONS_WITH_VALUE`，但没接通主流程）
  - legacy_all 兼容（README 明确说明：缺 `groups` 字段时按 `['all']` 处理；移植版没保留）
  - 端口冲突时排除"被覆盖用户自身端口"的细节（上游 `add_user` 第 477-479 行）
- `inventory/targets/users/testuser.yml` 仍是 `.yml` 扩展名 + JSON 内容 + **明文 private_key** —— 违背 plan §1.2「标准化格式」与「Vault 集成」两条承诺。

## 5. 发现与分析 (Findings)

### 5.1 Gemini 断言逐条评分

| # | Gemini 断言 | 真实情况 | 评级 |
|---|---|---|---|
| A1 | 「5 个积木」覆盖项目主体 | 漏 `roles/monitor/`、`audit.yml`、`reset.yml`、`generate_subs_gist.py`、`docker-build/`、单实例模式 | **不足** |
| A2 | Docker 隔离 / UID 10000 / 资源限制 | 属实；但仅适用 multi 模式，且具体值在 `group_vars/all/main.yml` 而非角色硬编码 | 部分 |
| A3 | 模拟 Microsoft 证书流量 | 实际 `reality_server_names = ["www.apple.com", "images.apple.com"]` | **错误** |
| A4 | "Docker-in-Docker 模式" | 实为 bind-mount 容器重执行，不是 DinD | **错误** |
| A5 | 标签驱动 ACL 路由（控制面预筛 + 执行面 outbound 调序） | 预筛属实；"outbound 调序"实际是单一 SOCKS5 出口的「按用户名单注入」，非通用调序；不存在 group→outbound 映射 | **误读** |
| M1 | "JSON-in-.yml 违反工程直觉" | 属实；但上游有理由（`from_yaml` 既兼容 JSON 又兼容 YAML，单 SSOT 输入双解析）；Gemini 自己的移植版**完全没修** | 部分（且未自洽） |
| M2 | "PrivateKey/UUID 明文存储" | 属实，且**比 Gemini 描述更严重**——已 push 到公开仓 29 份 | 严重不足 |
| M3 | `/tmp/reality_build` 硬编码冲突 | 路径属实；并发风险被夸大（单操作员场景几乎无碰撞，CI runner 才有） | 部分 |
| M4 | `synchronize` 模块依赖 rsync | 属实；上游已显式 `which rsync` 自检 + 友好失败提示 | 准确 |
| M5 | "审计缺失" | **错误**——存在 `audit.yml` 全网汇总 + `monitor/` 流量上报，Gemini 没看到 | **错误** |
| M6 | "健康检查简单：仅 restart: always" | 容器层属实；但项目层有 FastAPI monitor + cron agent | 部分（未提 monitor） |
| M7 | "Jinja2 模板嵌入大量 if/else，配置文件臃肿难调试" | multi 模板 128 行只有 2 个 `{% if %}`；single 模板只有 1 个 `{% for %}` | **错误** |
| M8 | "generate_user.py 自重写 Docker 逻辑过于复杂" | 实际 35 行 `docker run` 调用 + 父子参数桥接，意图清晰 | **夸大** |

合计：5 项**错误**或**严重不足**、5 项部分准确、3 项准确。**不能直接照搬。**

### 5.2 已落地产物的"反向回归"
- `scripts/manage_reality_users.py` 被宣传为"Ansispire 移植版"，实际是上游脚本的功能子集（去掉 update/delete/force/docker/legacy），但保留了上游被自己批评的"JSON-in-.yml"。
- `inventory/targets/users/testuser.yml` 自带明文 `private_key`，落地行为与 plan §1.2 完全相反。
- 综合判断：**Gemini 的实施动作与它自己的方案不一致**——这本身就是"不可信"的最直接证据。

### 5.3 真实功能盘点（用于替换 Gemini §1）
1. **节点编排控制面**（`deploy.yml`）—— ACL 预过滤 + 单/多实例分发 + 后置 Gist 推送。
2. **执行面（双模式）**：
   - `reality_single`：单容器多 inbound（端口随用户增长），适合用户少、节点上单进程更省内存的场景。
   - `reality_multi`：容器-per-用户（每用户独立 inbound + 独立 outbound 选择），具备资源隔离与单点 socks5 出口能力。
3. **出口策略**：仅 `reality_multi` 支持，机制是「`reality_socks5.target_users` 白名单 → 当前节点上该用户走 socks5 而非 freedom」，非通用路由表。
4. **可见性 ACL**（决定用户在节点上是否存在）：
   - 输入：`inventory.ini` 节点组 + `group_vars/all/main.yml::acl_matrix`（层级 + 特性矩阵）+ `users/*.yml::{groups, hosts}`。
   - 计算：deploy.yml pre_tasks 在每个节点上算 `reality_instances`。
5. **运维子系统**：
   - `monitor`：FastAPI 服务端（仅 `monitor.server_host` 节点）+ 全节点 agent + SQLite，自带 IP 白名单 / Bearer / report token 三层鉴权。
   - `audit.yml`：跨节点 access.log 抽 `email/srcIP` → 去重 → 汇总。
   - `reset.yml`：容器/数据/订阅缓存清理，支持 inventory 内外节点差异、二次确认、纯订阅模式。
   - `generate_subs_gist.py`：把 `/opt/reality/users/*_<host>.json` 聚合后 push 到 GitHub Gist。
   - `docker-build/`：自建 alpine + xray binary 镜像，作为 `xray_image` 默认源。
6. **用户管理 CLI**（`generate_user.py`）：add/update/delete/list，可选 `--docker` 容器内运行避免本机依赖。

### 5.4 真实缺陷清单（用于替换 Gemini §2）
1. **凭据治理**: 用户私钥明文且已入公网 git 历史 —— 不仅是"标准不符"，是**已发生的泄露**。迁移前必须先列出需要轮换的用户集（`users/*.yml` 全部 29 份）。
2. **SSOT 二义性**: `acl_matrix` 在 `group_vars/all/main.yml`、节点组在 `inventory.ini`、用户标签在 `users/*.yml`——三处变动一处忘改就静默错配。
3. **路径硬编码**: `/tmp/reality_build`、`/opt/reality/users` 控制端缓存路径无变量化，不是关键瓶颈但阻碍多操作员或 CI 化。
4. **rsync 依赖**: `synchronize` 模块对**控制端 + 目标端**都要 rsync；目标端已有自检，控制端无显式检查。
5. **`reality_mode` 默认值**: `reality_single` 是隐式默认，缺一个全局声明文档会让新手困惑。
6. **`monitor.yml` 遗留代码**: README 标注为"遗留不依赖"，但文件还在 → 维护混淆面。
7. **配置生效校验在控制端**: `docker compose config` 本地预校验属实是上游优点，但 `xray -test` 这一层 Gemini 提到的「预校验」**上游目前没有**，是 Gemini 把"建议"误标成"原项目缺陷"。

## 6. 结论与建议 (Conclusion)

### 6.1 总判决
- Gemini 的两份文档**不可作为实施依据**，但可作为"问题清单的起点"。需配合本报告的修订表使用。
- 已落地的 `scripts/manage_reality_users.py` 与 `inventory/targets/users/testuser.yml` 应视作**草稿，不是已迁移**——它们既不完整也违反自己的设计意图，建议在第一阶段重写。

### 6.2 推荐的修订迁移方案（取代 Gemini plan）

**阶段 0（前置，必须先做）—— 安全清算**
- 列出 reality-ops 公开 repo 中明文 `private_key` 涉及的所有用户（29 份），评估这些密钥是否仍在生产使用；若仍在用，先在迁移之前安排轮换。
- 这一阶段**不属于** Ansispire 迁移工作，但是迁移决策的前提（不能把已泄露的密钥再带到新系统）。

**阶段 1 —— 数据模型对齐**
- 在 Ansispire 制定 `users/<name>.yml` 的真 YAML 格式（不是 JSON-in-.yml），结构同上游但 `private_key` 字段用 `!vault | …` ansible-vault encrypt_string 内联加密。
- 在控制端读取时利用 `lookup('file', …) | from_yaml`（与上游兼容），渲染 config 时引用 `item.private_key`（Vault 字符串自动解密）。
- 删除 `scripts/manage_reality_users.py` 与 `inventory/targets/users/testuser.yml`，按新格式重写 CLI（保留上游 add/update/delete/list 全集 + 自动 vault encrypt_string 流程）。

**阶段 2 —— 控制面接入**
- 把 `acl_matrix` 落到 Ansispire 既有的分层 var 体系（建议放 `group_vars/all.yml` 或 Ansispire 的等价位置）；`inventory.ini` 的层级组（free/basic/…）映射到 Ansispire 的 inventory。
- 在 `deploy.yml` 等价 playbook 的 pre_tasks 复用上游 ACL 计算逻辑（Jinja 28 行块），不需要 filter plugin —— Gemini 提出的 filter plugin 抽象**纯属过度设计**，上游 28 行 Jinja 表达式可读性已足。

**阶段 3 —— 角色移植**
- 同时移植 `reality_single` 与 `reality_multi`（保留双模式，不要按 Gemini 只取 multi）。
- 把 `/tmp/reality_build` 替换为 `tempfile` 模块产出的工作目录或 Ansispire 标准缓存路径变量（这是 Gemini M3 提到但没在自己脚本里兑现的点）。
- `rsync` 检查同时加到控制端（pre-flight）和目标端。

**阶段 4 —— 配套子系统决策**
- `monitor/`：评估是否复用 Ansispire 自己的 EDA / 监控栈（如已有），不要直接照搬 FastAPI server——先做 gap 分析。
- `audit.yml`：迁移成本低，建议保留为 ad-hoc playbook。
- `reset.yml`：依赖于 `reality_data_dir` 等约定，移植后需逐条验证。
- `generate_subs_gist.py`：依赖 Gist + token，若 Ansispire 不打算暴露订阅，可以**直接砍掉**。
- `docker-build/`：建议**不要**移植——继续使用上游 `taoziyoyo2566/xray_docker:latest` 或 fork 一份固定 sha256 tag，避免维护自建镜像的负担。

**阶段 5 —— 验证**
- Molecule 场景：单实例 1 用户、单实例多用户、多实例 + ACL 矩阵交集、多实例 + socks5 target_users。
- 对照测试：用上游 deploy.yml + 同一 inventory 跑一遍，与 Ansispire 移植版生成的 `config.json` 做 diff，确保语义等价。

### 6.3 Gemini 提出但**应当拒绝**的"改进点"
- 「ACL Filter Plugin 抽象」：上游 Jinja 28 行已经能读，加 plugin 是反向复杂度。
- 「配置文件分片拼接 inbounds/outbounds/routing」：上游模板 128 行，分片会让现在能 grep 的东西变成需要执行渲染才能读懂的东西。
- 「容器日志接 Audit Plane」：等 Ansispire 的 Audit Plane 真有需求时再做，**当前没有**就不要把它当作迁移前置条件。
- 「AppArmor / Seccomp 自定义 profile」：与迁移目标无关，应剥离成独立 hardening 任务。
- 「management-container 预装加密库」：上游 `--docker` 已经解决同样问题，且更轻。

### 6.4 经验教训
- 跨 agent 移交方案前，**必须实际 clone 仓库读一遍**，不能依赖另一个 agent 的转述（命中 workspace W-R12 §a 同步更新原则）。
- 任何"已落地的移植代码"必须与方案文档对照检查"知行合一"，本次 Gemini 出现「方案说 YAML+Vault、代码写 JSON+明文」的反例。
- Ansispire CLAUDE.md §0 的"Proactive Challenge"在跨 agent 协作时尤其关键。

## 7. 关联验证 (Linked Verification)
- **TSVS 引用**: 尚未生成（属可行性研究而非 RCA，验证规格留待阶段 3 移植时建立）。
- **验证结果**: N/A —— 本次为方案复核，结论是"Gemini 方案不可直接照搬，须按 §6.2 修订"。

---
*Generated by Ansispire Investigation Engine — second-opinion on Gemini's reality-ops migration plan.*
