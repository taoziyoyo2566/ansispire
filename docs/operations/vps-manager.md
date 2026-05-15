# VPS Manager 运维指南 (Operational Reference)

> **本文档定位**：VPS Manager 插件的速查参考。命令为主、注释稀疏。
>
> **第一次接触？** 先看 [`plugins/vps_manager/README.md`](../../plugins/vps_manager/README.md) — 插件详细文档。

---

## 1. 核心逻辑

`vps_manager` 是一个轻量级 Ansispire 插件，用于 VPS 生命周期任务。它消耗 `runtime/inbox/vps/pending/` 中的一次性 YAML 任务，运行匹配的 Ansible playbook，并在 `runtime/state/vps_inventory.yml` 中维护长期状态。

---

## 2. 目录结构 (Runtime Layout)

```text
runtime/
  inbox/vps/
    drafts/       # 生成的草稿
    pending/      # 待处理任务 (process 命令扫描此处)
    processing/   # 正在处理中 (锁定)
    done/         # 成功完成的任务 (已脱敏)
    failed/       # 失败的任务 (含 *.error.json 报错信息)
    cancelled/    # 已取消的任务
    archived/     # 归档任务
  state/
    vps_inventory.yml   # 持久化 VPS 清单 (SSOT)
    tasks/              # 任务索引
  logs/vps_manager/     # 插件运行日志
```

---

## 3. 常用命令 (Makefile Wrappers)

### 3.1 任务全生命周期

| 命令 | 说明 |
|---|---|
| `make vps-new` | **交互式**创建 VPS onboarding 任务草稿 |
| `make vps-recover ALIAS=...` | **交互式**恢复已有 alias；确认后默认直接提交并处理当前任务 |
| `make vps-submit ALIAS=...` | 按唯一 alias 将草稿提交至 `pending/` 队列；多个匹配时改用 `FILE=...` |
| `make vps-tasks` | 列出所有任务及其状态 |
| `make vps-manager-process` | **处理** `pending/` 中的任务 (核心执行入口) |
| `make vps-manager-validate FILE=...` | 校验任务 YAML 文件合法性 |

### 3.2 维护与初始化

| 命令 | 说明 |
|---|---|
| `make vps-manager-init` | 初始化必要的运行时目录结构 |
| `make vps-manager-syntax` | 对所有 action playbook 进行 Ansible 语法检查 |
| `make test-vps-manager` | 运行 Python 单元测试 (逻辑校验) |

---

## 4. 故障排查 (Troubleshooting)

| 现象 | 修法 |
|---|---|
| 任务停在 `pending/` 不动 | 检查是否运行了 `make vps-manager-process`；检查文件权限。 |
| 任务进入 `failed/` | 查看 `failed/` 目录下同名的 `.error.json` 文件。 |
| `Validation failed: ssh.managed_port` | 项目红线：必须使用非 22 端口。修改任务 YAML 的 `ssh.managed_port`。 |
| `Alias already exists` | `onboard` 动作严禁覆盖。已纳管系统改配置用 `modify`；managed SSH 不可用但 bootstrap SSH 可用时用 `recover`。 |
| `Password environment variable not set` | 在执行 `process` 前 `export` 对应的环境变量，或在交互式模式下按提示输入。 |
| `Host is using the discovered Python interpreter` | VPS Manager 动态 inventory 会固定 `/usr/bin/python3`；如仍看到该警告，确认任务来自更新后的代码。 |

---

## 5. 安全审计红线

1. **禁止明文密码**：任务文件只允许包含环境变量名（`password_env`）。
2. **密钥管理**：`ansible_key` 用于自动化，`personal_keys` 用于操作员手动登录。
3. **脱敏归档**：`done/` 中的任务文件会自动擦除 `bootstrap` 字段。
4. **防火墙**：所有 `onboard` 任务默认开启 UFW 并限制 SSH 访问。

---

## 6. 关键文件引用

| 路径 | 说明 |
|---|---|
| `plugins/vps_manager/vps_manager.py` | 核心调度逻辑 |
| `plugins/vps_manager/schema.json` | 任务 YAML 的 JSON Schema 约束 |
| `runtime/state/vps_inventory.yml` | **本地 VPS 资产清单 (SSOT)** |
| `~/.ssh/ansispire_ssh_config` | (自动生成) 用于快捷登录受控主机的 SSH 配置 |

---
*Updated: 2026-05-15 (feat/vps-manager-plugin).*
