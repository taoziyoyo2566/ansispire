# Ansispire 快速上手指南 (Getting Started)

本指南旨在指导您完成系统的初始化、安全加固及管理中心（Hub）的部署。

---

## 1. 环境初始化 (Preparation)

在您的 **本地 PC** 或 **目标服务器** 上克隆代码并建立环境：

```bash
git clone https://github.com/your-username/ansispire.git
cd ansispire
make setup
source .venv/bin/activate
```

---

## 2. 核心决策：定义角色 (Configuration)

修改 `inventory/hosts.ini`。这是最重要的步骤，它决定了“谁是士兵，谁是指挥官”。

### 2.1 物理资产定义
在 `[all_vps]` 组下，确保您的服务器信息正确。

### 2.2 角色分配 (Hub 选址)
根据您的场景，在 `[hub]` 组中填入对应的机器名：

*   **场景 1：远程部署** (从电脑安装到 VPS) -> `[hub]` 下填入 `ans-hk01`。
*   **场景 2：本地自举** (已经在 VPS 上，安装到本机) -> `[hub]` 下填入 `control_node`。

---

## 3. 部署执行 (Execution)

部署分为两个逻辑阶段。请根据您的决策执行对应的命令。

### 阶段 I：系统安全加固 (System Baseline)
**目的**：配置防火墙、内核优化、SSH 安全及创建 `ansible` 运维用户。
建议对 **所有节点** 执行此操作。

*   **场景 1 (远程)**:
    ```bash
    ansible-playbook playbooks/site.yml -i inventory/hosts.ini -i inventory/dev -l ans-hk01
    ```
*   **场景 2 (本地)**:
    ```bash
    ansible-playbook playbooks/site.yml -i inventory/hosts.ini -i inventory/dev -l control_node
    ```

### 阶段 II：部署管理中心 (Hub Deployment)
**目的**：在选定的机器上安装 Semaphore 控制台及审计平面。
仅对 **[hub] 组** 成员执行。

*   **场景 1 (远程)**:
    ```bash
    ansible-playbook playbooks/deploy_hub.yml -i inventory/hosts.ini -i inventory/dev -l ans-hk01
    ```
*   **场景 2 (本地)**:
    ```bash
    ansible-playbook playbooks/deploy_hub.yml -i inventory/hosts.ini -i inventory/dev -l control_node
    ```

---

## 4. 验证与访问 (Verification)

部署完成后，管理中心将在 **3300 端口** 启动：
- **访问地址**: `http://<您的IP>:3300`
- **默认用户**: `admin` (密码见 `inventory/local/vault.yml`)

## 5. 架构原则 (Principles)
1. **先加固，后应用**：永远先运行 `site.yml` 确保系统处于安全基准状态。
2. **角色唯一性**：一个集群建议只保留一个 `[hub]` 节点，其余均为业务节点。
3. **外部维护**：Hub 的底层组件升级（如 Docker 变更）建议从外部触发。
