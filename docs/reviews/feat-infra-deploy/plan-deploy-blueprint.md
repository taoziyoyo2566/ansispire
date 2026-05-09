# Design RFC: Production Deployment Blueprint (Hub 1.0)

## 1. 目标与定位 (Goal)
构建一个“一键式”自动化部署方案，将 Ansispire 完整地安装在一台纯净的 Linux 主机（Ubuntu 22.04+）上。

### 核心特性
- **All-in-One**: 管理平面（Hub）与受控平面（Managed Node）合一。
- **Modern Stack**: 基于 Ansible-Core 2.20.5，强制 FQCN。
- **Safe Ports**: 核心端口锁定在 `3XXX` 区间（3000, 3010, 3020...）。
- **Secret First**: 强制使用 `ansible-vault` 处理敏感信息。

---

## 2. 软件基准规则 (Software Versioning Rules)
部署前将执行环境预检，低于以下版本的软件将触发强制升级：
- **Python**: 最低 3.10+ (Ansible 2.20 强制要求)
- **Docker Engine**: 最低 24.0.0+
- **Docker Compose Plugin**: 最低 2.20.0+

---

## 3. 架构设计 (Architecture)

### 3.1 角色定义 (Roles)
1. **`infra_baseline`**:
    - 安装 Python 3.10+ 环境。
    - 安装 Docker & Compose 插件。
    - 配置系统优化（Swap, Limit, Timezone）。
2. **`ansispire_hub`**:
    - 同步代码库（推荐：本地同步或 Git Clone）。
    - 使用 `ansible-vault` 加密变量生成 `.env`。
    - 启动 Semaphore 控制面板。
3. **`ansispire_audit`**:
    - 部署并启动审计平面（Sink, Relay, Reactor）。
    - 配置端口转发。

### 3.2 端口规划 (Port Matrix)
| 组件 | 端口 | 说明 |
| :--- | :--- | :--- |
| **Semaphore UI** | 3300 | 外部访问管理界面 (原 3000) |
| **Audit Sink** | 3310 | 内部审计日志接收端 (原 3010) |
| **EDA Webhook** | 3320 | (预留) 外部事件接收端口 (原 3020) |

---

## 4. 敏感信息管理 (Secret Strategy)
我们将使用 `inventory/local/vault.yml` 存储以下信息：
- `vault_semaphore_admin_password`: 初始管理员密码
- `vault_db_password`: 数据库密码（如适用）

安装流程将强制要求 `--ask-vault-pass`。

---

## 5. 部署流程 (Execution Flow)
1. **预检**: 检查端口冲突、磁盘空间、OS 版本。
2. **基础设施**: 更新软件包，安装 Docker。
3. **部署 Hub**: 创建目录结构 `/opt/ansispire`，同步代码，渲染配置文件。
4. **启动服务**: 启动容器编排。
5. **验证**: 执行回环测试 (Loop-smoke) 确保全链路打通。

---

## 6. 交互确认事项 (Feedback)
- **代码同步方案选择**：目前推荐使用 `ansible.builtin.synchronize` 从您的开发机直接同步当前工作目录。这能保证“所见即所得”，且包含您本地的所有补丁。您是否同意此方案？

---
*Created: 2026-05-09 | Ref: TASK-005*
