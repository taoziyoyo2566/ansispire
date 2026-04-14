# Semaphore 控制面 — 本地部署

Semaphore 是一个开源的 Ansible UI 控制面（Go 单进程 + SQLite/Postgres）。
本目录提供最小学习部署：Docker Compose + SQLite 后端，资源占用约 **200 MB RAM**。

---

## 目录作用

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | Semaphore 服务定义（镜像、卷、健康检查） |
| `.env.example` | 环境变量样例（管理员账号、端口等） |
| `.env` | 本地环境文件（**不提交 git**，见根 `.gitignore`） |
| `bootstrap.yml` | 通过 Semaphore API 创建 project/inventory/template 的 playbook |
| `README.md` | 本文件 |

---

## 首次启动（5 步）

```bash
# 1. 进入本目录
cd controller/semaphore

# 2. 复制环境样例并修改管理员密码
cp .env.example .env
vim .env        # 至少修改 SEMAPHORE_ADMIN_PASSWORD

# 3. 启动（从仓库根目录也可以 make controller-up）
docker compose --env-file .env up -d

# 4. 等待健康检查通过（约 30 秒）
docker compose ps

# 5. 浏览器打开 http://localhost:3000
#    用 .env 中的 SEMAPHORE_ADMIN / SEMAPHORE_ADMIN_PASSWORD 登录
```

---

## 首次启动后的初始化（bootstrap）

首次登录后，可运行 `bootstrap.yml` 自动创建一个最小可用的 project、inventory 和 job template：

```bash
# 从仓库根目录
ansible-playbook controller/semaphore/bootstrap.yml \
  -e semaphore_url=http://localhost:3000 \
  -e semaphore_user=admin \
  -e "semaphore_password=$(grep SEMAPHORE_ADMIN_PASSWORD controller/semaphore/.env | cut -d= -f2)"
```

bootstrap 完成后，Semaphore 里会出现：
- **Project**: `ansible-demo`
- **Repository**: 指向 `/workspace`（挂载的本 repo）
- **Inventory**: 指向 `inventory/production/hosts.ini`
- **Template**: `site.yml --check`（dry-run 任务）

此时可以在 Web UI 手动触发这个 template，观察 job output。

---

## 日常操作

```bash
# 查看日志
docker compose logs -f semaphore

# 重启
docker compose restart

# 停止（保留数据）
docker compose down

# 停止并清理数据（!! 会删除所有 project/job 历史 !!）
docker compose down -v
```

---

## 数据备份

Semaphore 状态存放在 Docker volume `semaphore-data`（BoltDB 文件）。

```bash
# 备份
docker run --rm \
  -v ansible-demo_semaphore-data:/data:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/semaphore-backup-$(date +%Y%m%d).tar.gz -C /data .

# 恢复
docker run --rm \
  -v ansible-demo_semaphore-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/semaphore-backup-YYYYMMDD.tar.gz -C /data
```

---

## 与本 repo 的集成

- 本 repo 被**只读挂载**到容器的 `/workspace`
- Semaphore 的 Repository 类型选 `Local`，路径填 `/workspace`
- 这样既能在 Semaphore UI 编辑 template，又能在本地用 git 管理 playbook 代码

---

## 常见问题

**Q: 为什么用 SQLite 而不是 Postgres？**
A: 学习场景，SQLite 零外部依赖。生产请改用 Postgres（修改 `docker-compose.yml` 中的 `SEMAPHORE_DB_DIALECT`）。

**Q: 端口 3000 被占用？**
A: 在 `.env` 中修改 `SEMAPHORE_PORT`（例如 `3001`）。

**Q: 管理员密码忘了？**
A: 进入容器重置：
```bash
docker compose exec semaphore semaphore user change-by-login --login admin --password <new>
```

**Q: 如何升级到 AWX？**
A: 见上层 `controller/README.md` 的「升级路径」。
