# 测试规格与验证说明书 (TSVS) - Molecule webserver 场景

## 1. 测试概览 (Overview)
- **测试 ID**: `TSVS-MOL-WEBSERVER-001`
- **测试类型**: L4 集成测试 (Integration / Molecule)
- **优先级**: 高 (P0)
- **测试目的**: 验证 `roles/webserver` 在 Ubuntu 22.04 + Debian 12 上部署后，Nginx 服务存活、配置语法通过、默认 vhost 与 index 文件落盘、HTTP 端口可达，并通过 Molecule idempotence 阶段验证二次执行无变更。本场景同时承担 round-5 修复（`ansible_managed | comment` 在 `nginx.conf.j2`/`vhost.conf.j2`）的回归防线。
- **覆盖表面**: [`roles/webserver/`](../../../roles/webserver/) → [`test-plan.md §4.2`](../../governance/test-plan.md)

## 2. 测试环境 (Environment)
- **驱动**: docker
- **被测平台**:
  - `ubuntu22-webserver`: `geerlingguy/docker-ubuntu2204-ansible:latest`（Ubuntu 22.04 LTS，systemd）
  - `debian12-webserver`: `geerlingguy/docker-debian12-ansible:latest`（Debian 12 Bookworm，systemd） — 2026-05-12 G3 引入
- **容器参数**: `privileged: true`、`cgroupns_mode: host`、`/sys/fs/cgroup` rw、`command: /lib/systemd/systemd`
- **测试 vhost**: `name: test.local`、`root: /var/www/html`、`ssl: false`、`php_fpm: false`
- **测试端口**: 容器内 80（不映射到宿主，由 verify.yml 在容器内 `curl http://localhost/` 验证）
- **执行宿主**: 任何能跑 docker 的 Linux/macOS 工作站；CI 使用 `ubuntu-latest`

## 3. 软件包清单 (Software Stack)
| 软件名称 | 版本号 | 备注 |
| :--- | :--- | :--- |
| ansible-core | 2.20.5 | |
| molecule | >= 24.0.0 | |
| molecule-plugins[docker] | >= 23.5.0 | |
| Python | 3.11 | CI baseline |
| nginx | Ubuntu 22.04 / Debian 12 APT 默认版本 | OS-family map: `_webserver__nginx_packages.Debian: nginx`（同包名两个发行版均可用） |

## 4. 测试方法与步骤 (Methodology)

### 4.1 前置条件 (Prerequisites)
1. `make setup` / `pip install -r requirements.txt` 完成。
2. Galaxy 依赖已安装。
3. Docker daemon 运行中。
4. group_vars 中 `webserver__vhosts` 已声明（由 molecule.yml `provisioner.inventory.group_vars.all` 注入）。

### 4.2 执行步骤 (Steps)
1. **干净验证**：`molecule test -s webserver`
   - 完整生命周期：`dependency → cleanup → destroy → syntax → create → prepare → converge → idempotence → verify → cleanup → destroy`
   - `converge` 阶段会在 `prepare.yml` 后串接 `converge.yml` 与 `verify.yml`（由 `provisioner.playbooks` 显式指向）
2. **迭代调试**：`molecule converge -s webserver`
3. **登入容器**：`molecule login -s webserver`，便于直接 `curl`、`nginx -T` 排查
4. **手动 verify**：`molecule verify -s webserver`，无需重建容器

## 5. 预期结果 (Expected Results)

`verify.yml` 5 项断言全部 PASS：

- [x] `'nginx' in services and services['nginx'].state == 'running'`（`service_facts` + `assert`）
- [x] `nginx -t` 命令退出码 0（容器内执行）
- [x] `http://localhost/` 响应 HTTP `[200, 301, 302]`（`ansible.builtin.uri`）
- [x] 文件 `/var/www/html/index.html` 存在
- [x] 文件 `/etc/nginx/sites-available/test.local.conf` 存在

idempotence 阶段：第二次 converge **必须 0 changed**。

### 5.1 间接覆盖（round-5 修复回归防线）
- 模板 `ansible_managed | comment`：若回归（去掉 `| comment` 过滤器），`nginx -t` 会因为 bare 字符串被解析为未知 directive 而失败 → 通过 §5 第 2 条断言间接捕获。
- `webserver__vhosts` 变量统一化（去除 `nginx_vhosts` legacy alias）：若任意调用方误用旧名，渲染会失败或得到空 vhost，间接由 §5 第 5 条与 §5 第 4 条捕获。

### 5.2 未断言的项（已知盲区，登记给未来 TSVS）
- SSL 证书加载（场景显式 `ssl: false`）
- PHP-FPM 集成（场景显式 `php_fpm: false`）
- 多 vhost 路由（仅一个 `test.local`）
- 限流 / `client_max_body_size` 等具体 nginx 参数

## 6. 测试执行记录 (Actual Results)
- **执行时间**: 由 CI 持续维护；本 round 2 未触发独立 ad-hoc 运行
- **执行人**: GitHub Actions `molecule` job（matrix scenario = `webserver`）
- **状态**: 由 CI 状态决定
- **实际表现**:
    > 首次完整执行结果待落地后追溯（plan §6 round 2 仅登记现有断言，不引入新断言）。
- **异常分析**: 无（round-5 `ansible_managed | comment` 修复后未观察到回归）

## 7. 结论与建议 (Conclusion)
- **测试结论**: 当前结构以"服务存活 + 配置正确 + HTTP 可达 + 落盘文件存在 + idempotence" 5 条覆盖 webserver role 的 happy path；可回归 round-5 nginx 启动失败 bug。
- **建议**：
  - ~~**多 distro 扩展**（G3）：当前仅 Ubuntu 22.04，未来引入 Debian 12 平台。~~ ✅ **CLOSED 2026-05-12**（Tier C round 2）：Debian 12 平台已加入；两平台均跑 verify.yml 5 条断言。
  - **SSL / PHP-FPM 子场景**：可作为独立 TSVS 引入（不在本场景断言范围）。
  - **G8 收口**：模板渲染产物只能由 Molecule 兜底——这是本场景必须长期保留的根本理由，记入 §5.1。

---
*Carrier: `molecule test -s webserver` (≈ 2–5 min) | CI `molecule` matrix*
*Registered in: [`docs/reference/test-specs/INDEX.md`](INDEX.md)*
