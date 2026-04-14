---
name: Round Progress Tracker
description: Current state of the management control system roadmap (Rounds 5-12); updated per round
type: project
originSessionId: 9c81eec7-62c3-4d7d-a3d9-c075fe4666d9
---
**最近更新**: 2026-04-14

## 已落地

- **Round 5**（工程层地基）：工具链、安全默认、测试补强、面向未来预留
  - changelog: `docs/reviews/round-5-change-log-2026-04-14.md`
- **Round 7**（控制面 PoC）：Semaphore + Docker Compose + SQLite，验证通过
  - changelog: `docs/reviews/round-7-change-log-2026-04-14.md`
  - 运行状态：容器 `ansible-demo-semaphore` 已启动，端口 3001（宿主 3000 被占用）
  - 资源：6.6 MB RAM；workspace 只读挂载到 /workspace

## 已方案化未实施（归档态）

- **Round 8**（IAM + 凭证集中 + 轻量审计）
  - 方案: `docs/reviews/claude-review-round-8-2026-04-14.md`
  - 状态: 2026-04-14 用户决定暂缓
  - 恢复入口: 方案第 14 节授权清单
  - 范围调整要点: OIDC 推迟到 Round 11，Loki 审计推迟到 Round 9，凭证集中前置到 Round 8

## 待规划

- Round 9：可观测性栈（Prometheus + Grafana 最小）
- Round 10：密钥管理升级（HashiCorp Vault 后端）
- Round 11：事件驱动 + 集成（EDA + ITSM webhook + OIDC SSO 评估）
- Round 12：多租户 + DR

## 关键决策锚点

- 控制器选型：**Semaphore**（2026-04-14 用户批准，理由：~200 MB RAM 匹配 1 GB 预算）
- 部署形态：Docker Compose 起步，未来可升级 k3s
- 密钥后端：当前 ansible-vault，Round 10 考虑迁移
- 可观测性栈：最小 Prometheus + Grafana（Round 9）
- 宿主规格：8c16g（R7 授权自主执行本地非破坏性操作）

## How to apply

- 新会话开始时读此文件 + MEMORY.md 确定当前位置
- 用户说"继续 Round N"或"进入下一轮"时，先查此文件的归档态列表
- 每轮 changelog 写完后更新此文件"已落地"节
