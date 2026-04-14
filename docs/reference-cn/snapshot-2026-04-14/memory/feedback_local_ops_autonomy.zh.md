---
name: Local Operations Autonomy
description: User authorizes autonomous local docker/process ops on 8c16g host; only destructive or host-modifying ops need confirmation
type: feedback
originSessionId: 9c81eec7-62c3-4d7d-a3d9-c075fe4666d9
---
**规则**：对系统无破坏性影响的本地操作可直接执行，不需逐次请求同意。

**可自主执行**：
- 启动/停止 docker 容器、compose 栈
- 创建/销毁容器实例（非宿主机层面）
- 本地端口监听
- 只读验证（curl localhost、docker inspect、logs）
- 读取文件、跑测试、跑 dry-run

**仍需请求同意**：
- 修改宿主配置（/etc, systemd, 用户/组）
- 安装系统包（apt/yum/pacman）
- 修改防火墙/网络规则
- 对外发起网络请求（除本地 API 调试）
- 破坏性清理：`rm -rf`、`docker volume rm`、`docker system prune`、`docker compose down -v`
- 涉及密钥/证书落盘
- git push、git reset --hard

**Why**：用户明确授权（2026-04-14，Round 7 验证节点）。宿主是 8c16g 资源服务器，资源充足，风险可控前提下希望 Claude 快速推进。

**How to apply**：
- 执行前先说明要做什么（一句话）
- 每个操作有输出记录（logs、docker ps 等）
- 失败时立即停止并报告，不要自动清理
- 需要确认的操作按老规则照常询问

同步位置：CLAUDE.md 第 7 节 R7 规则。
