# feat-target-architecture — Semaphore Runtime Probe Archive

**Date**: 2026-06-06
**Branch**: `feat/target-architecture`
**Purpose**: Preserve the runtime probes that were run before starting the CF Worker Wizard implementation.
**Related evidence**:

- [`docs/reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md`](../../reference/investigations/IVG-SEMAPHORE-INVENTORY-API.md)
- [`docs/reviews/feat-target-architecture/round7-2026-06-06.changelog.md`](../feat-target-architecture/round7-2026-06-06.changelog.md)
- [`docs/reviews/feat-target-architecture/round8-2026-06-06.changelog.md`](../feat-target-architecture/round8-2026-06-06.changelog.md)

---

## Why This Probe Existed

The CF Worker Wizard was supposed to become the operator-facing entry point for adding and managing VPS nodes through Semaphore. Before writing that Worker, two assumptions had to be verified against the live Semaphore runtime instead of only relying on design notes:

1. Whether Semaphore `static` inventory can be managed as a whole INI blob through the Inventory API.
2. Whether a Worker can pass structured lifecycle input into an Ansible task as top-level `vps_task`.

Without this probe, the Worker could have been built around the wrong contract:

- a fake per-host inventory API that Semaphore does not expose;
- raw `extra_vars` task input that was not confirmed at runtime;
- a payload shape that does not match `playbooks/vps/onboard.yml`.

The probe therefore acted as a gate: only after the inventory and task payload contracts were confirmed did Round 8 implement `cf-worker/`.

---

## Runtime Context

| Item | Value | Why it mattered |
|---|---|---|
| Semaphore image | `semaphoreui/semaphore:v2.18.2` | The Worker contract must match the runtime version used by the controller. |
| Semaphore URL | `http://127.0.0.1:3300` | Local API endpoint for the live controller instance. |
| Project | `ansispire`, project id `1` | Scope for inventory, templates, keys, and tasks. |
| Existing inventory | `targets-managed`, inventory id `2` | Confirmed the current production-facing inventory was still `type: file`. |
| Probe static inventory | `__probe_static_inventory__`, inventory id `3` | Temporary DB-backed inventory used to verify static blob CRUD. |
| Probe template | `__probe_vars_template__`, template id `5` | Temporary task template used only to prove task variable injection. |
| Probe tasks | task id `1` and task id `2` | Task `1` tested raw `extra_vars`; task `2` tested task-level `environment`. |

---

## Variables Set During The Probe

These variables were set to avoid mixing project, inventory, and template ids while calling the Semaphore API by hand.

| Variable | Value | Purpose |
|---|---:|---|
| `SEMAPHORE_PROJECT_ID` | `1` | Project scope for all `/api/project/{id}/...` calls. |
| `SEMAPHORE_TARGETS_INVENTORY_ID` | `2` | Existing `targets-managed` inventory to inspect before creating a probe inventory. |
| `SEMAPHORE_PING_TEMPLATE_ID` | `4` | Existing "Ping all targets" template used for the first task-launch probe. |
| `SEMAPHORE_PROBE_INVENTORY_ID` | `3` | Temporary static inventory created by the probe. |
| `SEMAPHORE_PROBE_TEMPLATE_ID` | `5` | Temporary template pointing at the probe playbook. |
| `SEMAPHORE_EXTRA_VARS_TASK_ID` | `1` | Task created with a raw `extra_vars` body. |
| `SEMAPHORE_PROBE_ENV_TASK_ID` | `2` | Task created with task-level `environment` JSON. |

The login cookie was created with credentials from `controller/semaphore/.env`, using:

```bash
USER_=$(grep '^SEMAPHORE_ADMIN=' controller/semaphore/.env | cut -d= -f2)
PASS_=$(grep '^SEMAPHORE_ADMIN_PASSWORD=' controller/semaphore/.env | cut -d= -f2)

curl -sS -c /tmp/semaphore.cookie \
  -H 'Content-Type: application/json' \
  -d "{\"auth\":\"$USER_\",\"password\":\"$PASS_\"}" \
  http://127.0.0.1:3300/api/auth/login
```

The cookie was used instead of embedding credentials in every probe request.

---

## Probe 1: Confirm The Existing Inventory State

### Question

Is the current `targets-managed` inventory already DB-backed `static`, or is it still a repository file inventory?

### Request

```bash
curl -sS -b /tmp/semaphore.cookie \
  "http://127.0.0.1:3300/api/project/${SEMAPHORE_PROJECT_ID}/inventory/${SEMAPHORE_TARGETS_INVENTORY_ID}"
```

### Result

Semaphore returned:

```json
{
  "id": 2,
  "name": "targets-managed",
  "project_id": 1,
  "inventory": "inventory/hosts.ini",
  "ssh_key_id": 2,
  "type": "file"
}
```

### Meaning

The production-facing inventory had not migrated to DB-backed static content yet. The Worker could not assume inventory id `2` was safe for live blob mutation. A separate probe inventory was required.

---

## Probe 2: Create A Static Inventory

### Question

Can Semaphore persist an INI inventory blob directly through `POST /inventory` with `type: static`?

### Request

```json
{
  "name": "__probe_static_inventory__",
  "project_id": 1,
  "inventory": "[vps_targets]\nprobe ansible_host=127.0.0.1 ansible_user=ansible ansible_port=1156\n",
  "type": "static",
  "ssh_key_id": 2
}
```

### Result

Semaphore returned `HTTP_STATUS=201` and created inventory id `3`.

### Meaning

The Worker can create DB-backed static inventories. The input model should treat `.inventory` as a complete text blob, not as per-host rows.

---

## Probe 3: Read A Static Inventory Blob

### Question

Does `GET /inventory/{id}` return the full static inventory content that the Worker needs to parse and mutate?

### Request

```bash
curl -sS -b /tmp/semaphore.cookie \
  "http://127.0.0.1:3300/api/project/${SEMAPHORE_PROJECT_ID}/inventory/${SEMAPHORE_PROBE_INVENTORY_ID}"
```

### Result

Semaphore returned `HTTP_STATUS=200` and included the full INI content:

```json
{
  "id": 3,
  "name": "__probe_static_inventory__",
  "inventory": "[vps_targets]\nprobe ansible_host=127.0.0.1 ansible_user=ansible ansible_port=1156\n",
  "type": "static"
}
```

### Meaning

The Worker can implement read-modify-write behavior by fetching the whole inventory object, parsing `[vps_targets]`, and serializing the mutated blob back to Semaphore.

---

## Probe 4: Update A Static Inventory Blob

### Question

Does `PUT /inventory/{id}` replace the static inventory blob, and what response shape should the Worker expect?

### Request

```json
{
  "id": 3,
  "name": "__probe_static_inventory__",
  "project_id": 1,
  "inventory": "[vps_targets]\nprobe2 ansible_host=127.0.0.2 ansible_user=ansible ansible_port=1156\n",
  "type": "static",
  "ssh_key_id": 2
}
```

### Result

`PUT` returned `HTTP_STATUS=204` with no body. A follow-up `GET` returned the replacement INI blob.

### Meaning

The Worker should treat update as whole-object replacement and should not expect a response body after a successful update. This directly shaped `cf-worker/src/semaphore.js` and `cf-worker/src/inventory.js`.

---

## Probe 5: Test Raw `extra_vars`

### Question

Can the Worker send runtime lifecycle input through a raw `extra_vars` field in `POST /tasks`?

### Request

```json
{
  "template_id": 4,
  "extra_vars": {
    "vps_task": {
      "probe": true,
      "source": "phase1-runtime-probe"
    }
  }
}
```

### Result

Semaphore accepted the task request with `HTTP_STATUS=201`, but the task ended in `error`.

The output showed the existing `Ping all targets` template tried to connect to real inventory hosts and failed because the Semaphore container did not have the expected SSH identity:

```text
no such identity: /home/semaphore/.ssh/ansible: No such file or directory
Permission denied (publickey,...)
```

The task detail did not prove that raw `extra_vars` reached Ansible.

### Meaning

This did not establish `extra_vars` as a safe Worker contract. The failure was useful because it showed the existing ping template was a poor variable-injection probe: it mixed task payload testing with real host connectivity and SSH-key availability.

---

## Probe 6: Create A Dedicated Variable Injection Template

### Question

Can the task payload be tested without depending on real VPS connectivity?

### Setup

A temporary template named `__probe_vars_template__` was created against the probe static inventory. It pointed at a temporary probe playbook that only printed `vps_task`.

### Result

Semaphore created template id `5` with `HTTP_STATUS=201`.

### Meaning

The variable-injection test was isolated from SSH reachability. This made the next result meaningful: if Ansible printed `vps_task`, the task launch payload worked.

---

## Probe 7: Test Task-Level `environment`

### Question

Can the Worker pass structured runtime input through the task-level `environment` field?

### Request

```json
{
  "template_id": 5,
  "environment": "{\"vps_task\":{\"probe\":true,\"source\":\"task-environment-field\"}}"
}
```

### Result

Semaphore returned `HTTP_STATUS=201`. Task detail preserved the `environment` string, and task output showed Ansible received:

```json
{
  "vps_task": {
    "probe": true,
    "source": "task-environment-field"
  }
}
```

The task completed with `status: success`.

### Meaning

This established the runtime payload contract used by the Worker:

```js
environment: JSON.stringify({ vps_task })
```

It also confirmed that the lifecycle playbooks can continue using top-level `vps_task` rather than introducing separate ad hoc variables.

---

## Final Design Decisions Produced By The Probe

| Decision | Evidence |
|---|---|
| Worker inventory CRUD uses whole-blob read-modify-write. | Static inventory create/read/update probes succeeded. |
| Worker parser targets INI `[vps_targets]`. | Semaphore preserved the INI blob exactly. |
| Worker update path expects `204` and no body. | Static inventory `PUT` returned `204`; follow-up `GET` confirmed replacement. |
| Worker task launch uses task-level `environment`. | Dedicated probe template received `vps_task` through `environment`. |
| Raw `extra_vars` is not the Worker contract. | It was accepted by the API but not proven to reach Ansible. |
| Existing `targets-managed` inventory remains unmigrated. | Inventory id `2` is still `type: file`. |

---

## Effect On Round 8 Implementation

The probe directly justified these implementation choices:

- `cf-worker/src/inventory.js` parses and serializes the inventory blob instead of calling non-existent per-host endpoints.
- `cf-worker/src/semaphore.js` sends complete inventory objects on update and handles `204` as success.
- `SemaphoreClient.triggerTask()` serializes task data as `environment: JSON.stringify({ vps_task })`.
- `cf-worker/wrangler.toml` keeps real template ids empty until the onboard/audit templates are provisioned and verified.
- Round 8 deliberately does not migrate production `targets-managed` from `file` to `static`; that remains Phase 3 work.

---

## Cleanup State

The runtime probe created temporary Semaphore resources:

| Resource | ID | Cleanup recommendation |
|---|---:|---|
| `__probe_static_inventory__` | `3` | Delete after no further live replay is needed. |
| `__probe_vars_template__` | `5` | Delete after no further live replay is needed. |
| Probe task history | `1`, `2` | Leave as historical task logs unless the controller instance is reset. |

Suggested cleanup:

```bash
curl -sS -w '\nHTTP_STATUS=%{http_code}\n' -X DELETE -b /tmp/semaphore.cookie \
  "http://127.0.0.1:3300/api/project/${SEMAPHORE_PROJECT_ID}/templates/5"

curl -sS -w '\nHTTP_STATUS=%{http_code}\n' -X DELETE -b /tmp/semaphore.cookie \
  "http://127.0.0.1:3300/api/project/${SEMAPHORE_PROJECT_ID}/inventory/3"
```

---

## Final Outcome

The probe closed the Worker-critical contract gap:

1. Semaphore `static` inventory supports whole-blob CRUD for INI content.
2. Task-level `environment` can carry nested `vps_task` into Ansible.
3. Raw `extra_vars` should not be used as the Worker contract.
4. The Worker Wizard implementation could proceed with a verified API model instead of relying on design assumptions.
