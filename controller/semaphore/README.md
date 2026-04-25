# Semaphore Control Plane — Local Deployment

Semaphore is an open-source Ansible UI control plane (Go single-process + BoltDB/Postgres).
This directory provides a minimal learning deployment: Docker Compose + BoltDB backend, using about **200 MB RAM**.

> Chinese reference snapshot: `../../docs/reference-cn/snapshot-2026-04-14/controller/semaphore/README.zh.md`

---

## What's in This Directory

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Semaphore service definition (image, volumes, healthcheck) |
| `.env.example` | Environment variable template (admin account, port, etc.) |
| `.env` | Local environment file (**not committed to git**; see root `.gitignore`) |
| `bootstrap.yml` | Playbook that creates project/inventory/template through the Semaphore API |
| `README.md` | This file |

---

## First Start (5 steps)

```bash
# 1. Enter this directory
cd controller/semaphore

# 2. Copy the env template and set the admin password
cp .env.example .env
vim .env        # at minimum, change SEMAPHORE_ADMIN_PASSWORD

# 3. Start (from the repo root you can instead run `make controller-up`)
docker compose --env-file .env up -d

# 4. Wait for the healthcheck to pass (about 30 seconds)
docker compose ps

# 5. Open http://localhost:3000 in a browser
#    Log in with SEMAPHORE_ADMIN / SEMAPHORE_ADMIN_PASSWORD from .env
```

---

## Post-Start Initialization (bootstrap)

After the first login, run `bootstrap.yml` to automatically create a minimal working project, inventory, and job template:

```bash
# From the repo root
ansible-playbook controller/semaphore/bootstrap.yml \
  -e semaphore_url=http://localhost:3000 \
  -e semaphore_user=admin \
  -e "semaphore_password=$(grep SEMAPHORE_ADMIN_PASSWORD controller/semaphore/.env | cut -d= -f2)"
```

After bootstrap completes, Semaphore will contain:
- **Project**: `ansispire`
- **Repository**: points to `/workspace` (this repo, mounted into the container)
- **Inventory**: points to `inventory/production/hosts.ini`
- **Template**: `site.yml --check` (dry-run task)

You can then trigger this template manually from the Web UI and watch the job output.

---

## Daily Operations

```bash
# Follow logs
docker compose logs -f semaphore

# Restart
docker compose restart

# Stop (keep data)
docker compose down

# Stop and remove data (!! deletes all projects and job history !!)
docker compose down -v
```

---

## Data Backup

Semaphore state is stored in the Docker volume `semaphore-data` (BoltDB file).

```bash
# Backup
docker run --rm \
  -v semaphore_semaphore-data:/data:ro \
  -v $(pwd):/backup \
  alpine tar czf /backup/semaphore-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore
docker run --rm \
  -v semaphore_semaphore-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/semaphore-backup-YYYYMMDD.tar.gz -C /data
```

---

## Integration With This Repo

- This repo is mounted **read-only** at `/workspace` inside the container
- Use Repository type `Local` in Semaphore and set the path to `/workspace`
- That way you can edit templates in the Semaphore UI while still managing the playbook code locally with git

---

## FAQ

**Q: Why BoltDB instead of Postgres?**
A: This is a learning setup. BoltDB is a pure Go key-value store that allows Semaphore to run with **zero external dependencies** and minimal memory overhead (~200MB). For production scaling or high availability, you should switch to Postgres by changing `SEMAPHORE_DB_DIALECT` in `docker-compose.yml`.

**Q: Port 3000 already in use?**
A: Change `SEMAPHORE_PORT` in `.env` (for example `3001`).

**Q: Forgot the admin password?**
A: Reset it from inside the container:
```bash
docker compose exec semaphore semaphore user change-by-login --login admin --password <new>
```

**Q: How do I upgrade to AWX?**
A: See "Upgrade Path" in the parent `controller/README.md`.
