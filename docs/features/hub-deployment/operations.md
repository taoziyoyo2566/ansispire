# Ansispire Hub 运维指南 (Operational Guideline)

## 1. 核心架构说明 (Architecture)
Ansispire Hub 采用 **All-in-One** 架构，将管理平面与执行平面集成在单台主机上。

- **控制中心 (Semaphore)**: 提供 Web UI 和 API 调度任务。
- **审计平面 (Audit Plane)**: 实时捕获操作日志并持久化为 JSONL 格式。
- **反应引擎 (EDA Reactor)**: 监听审计日志，触发自动化自愈逻辑。

## 2. 端口与访问 (Network)
为了避免端口冲突并保持识别度，系统统一使用 `33XX` 端口区间：
- **3300**: Semaphore 管理后台 (http://<IP>:3300)
- **3310**: Audit Sink (API 接收端)
- **3320**: EDA Reactor (预留)

## 3. 用户与权限 (Security)
- **ansible 用户**: 部署流程会自动创建名为 `ansible` 的专用系统用户，具备免密 `sudo` 权限。
- **SSH 连接**: 后续维护建议使用 `ansible` 用户通过密钥连接，逐步替代 `root`。
- **基础设施维护**: **禁止通过 Hub 自身的 Semaphore 调度任务来维护或升级 Hub 的基础设施**。Hub 的升级、Docker 配置变更以及关键漏洞补丁必须从外部（如本地开发机）通过 `playbooks/deploy_hub.yml` 触发。

## 4. 常用维护命令 (Maintenance)
进入部署目录 `/opt/ansispire` 后执行：
- **查看服务状态**: `docker compose -f controller/semaphore/docker-compose.yml ps`
- **重启审计平面**: `docker compose -f controller/audit/docker-compose.yml restart`
- **查看实时审计流**: `tail -f /var/log/semaphore/events.jsonl` (在 Sink 容器或挂载路径)

## 5. 常见问题 (FAQ)
- **为什么需要部署 Semaphore Hub?**
  它是全系统的“自动化调度中枢”。在生产环境中，Hub 应部署在独立的、受保护的管理节点上。通过 Hub，您可以实现 API 触发的任务调度、集中式密钥管理、持久化执行日志，以及基于审计流的自动自愈逻辑。
- **目标 VPS 可以作为 Hub 吗？**
  可以，但仅建议在初期实验或资源受限环境下使用 (All-in-One 模式)。生产环境下建议物理分离，以避免业务负载影响管理系统的稳定性。
