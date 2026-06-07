import worker from "../src/index.js";
import { SemaphoreClient } from "../src/semaphore.js";

const MUTATION_CONFIRM = "mutate-static-inventory";
const DEFAULT_PROBE_ALIAS = `worker-live-probe-${Date.now()}`;

await main().catch((err) => {
  console.error(err.message || err);
  process.exitCode = 1;
});

async function main() {
  const env = buildWorkerEnv();
  const client = new SemaphoreClient({
    url: env.SEMAPHORE_URL,
    token: env.SEMAPHORE_API_TOKEN
  });
  const readOnly = process.env.WORKER_LIVE_READ_ONLY === "1";
  const allowMutation = process.env.WORKER_LIVE_CONFIRM === MUTATION_CONFIRM;
  const probeAlias = process.env.WORKER_LIVE_PROBE_ALIAS || DEFAULT_PROBE_ALIAS;
  let originalInventory = null;
  let mutated = false;

  try {
    originalInventory = await client.getInventory(env.SEMAPHORE_PROJECT_ID, env.SEMAPHORE_INVENTORY_ID);
    assertStaticInventory(env, originalInventory);
    assertWorkerUpdateCompatible(originalInventory);

    await callWorker(env, "GET", "/health");
    const initial = await callWorker(env, "GET", "/vps");
    console.log(`GET /vps ok (${initial.hosts.length} hosts)`);

    if (readOnly) {
      console.log("Read-only live integration completed.");
      return;
    }

    if (!allowMutation) {
      throw new Error(`Set WORKER_LIVE_CONFIRM=${MUTATION_CONFIRM} to run mutation checks against a probe static inventory.`);
    }

    if (initial.hosts.some((host) => host.alias === probeAlias)) {
      throw new Error(`Probe alias already exists: ${probeAlias}`);
    }

    await callWorker(env, "POST", "/vps", {
      alias: probeAlias,
      ip: "192.0.2.55",
      port: 2222,
      user: "ansible"
    });
    mutated = true;
    console.log(`POST /vps ok (${probeAlias})`);

    const afterCreate = await callWorker(env, "GET", "/vps");
    assertHost(afterCreate.hosts, probeAlias, { ip: "192.0.2.55", port: 2222 });

    await callWorker(env, "PUT", `/vps/${encodeURIComponent(probeAlias)}`, {
      ip: "192.0.2.56",
      port: 2223,
      user: "ansible"
    });
    console.log(`PUT /vps/${probeAlias} ok`);

    const afterUpdate = await callWorker(env, "GET", "/vps");
    assertHost(afterUpdate.hosts, probeAlias, { ip: "192.0.2.56", port: 2223 });

    await callWorker(env, "DELETE", `/vps/${encodeURIComponent(probeAlias)}`);
    console.log(`DELETE /vps/${probeAlias} ok`);

    const afterDelete = await callWorker(env, "GET", "/vps");
    if (afterDelete.hosts.some((host) => host.alias === probeAlias)) {
      throw new Error(`Probe alias still exists after delete: ${probeAlias}`);
    }

    console.log("Live integration completed. Original inventory will be restored.");
  } catch (err) {
    console.error(err.message || err);
    process.exitCode = 1;
  } finally {
    if (mutated && originalInventory) {
      try {
        await client.updateInventory(env.SEMAPHORE_PROJECT_ID, originalInventory);
        console.log("Restored original Semaphore inventory blob.");
      } catch (err) {
        console.error(`Failed to restore original Semaphore inventory blob: ${err.message || err}`);
        process.exitCode = 1;
      }
    }
  }
}

function buildWorkerEnv() {
  const requiredKeys = [
    "SEMAPHORE_URL",
    "SEMAPHORE_API_TOKEN",
    "SEMAPHORE_PROJECT_ID",
    "SEMAPHORE_INVENTORY_ID",
    "WORKER_AUTH_USER",
    "WORKER_AUTH_PASSWORD"
  ];
  const missing = requiredKeys.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing required env vars: ${missing.join(", ")}`);
  }

  return {
    SEMAPHORE_URL: process.env.SEMAPHORE_URL,
    SEMAPHORE_API_TOKEN: process.env.SEMAPHORE_API_TOKEN,
    SEMAPHORE_PROJECT_ID: process.env.SEMAPHORE_PROJECT_ID,
    SEMAPHORE_INVENTORY_ID: process.env.SEMAPHORE_INVENTORY_ID,
    SEMAPHORE_ONBOARD_TEMPLATE_ID: "",
    SEMAPHORE_AUDIT_TEMPLATE_ID: "",
    WORKER_AUTH_USER: process.env.WORKER_AUTH_USER,
    WORKER_AUTH_PASSWORD: process.env.WORKER_AUTH_PASSWORD
  };
}

async function callWorker(env, method, path, body) {
  const init = {
    method,
    headers: {
      Authorization: basicAuthHeader(env)
    }
  };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const response = await worker.fetch(new Request(`https://worker.local${path}`, init), env, {});
  const text = await response.text();
  const data = parseResponse(text);
  if (!response.ok) {
    throw new Error(`${method} ${path} failed with ${response.status}: ${data?.error || text}`);
  }
  return data;
}

function basicAuthHeader(env) {
  return `Basic ${Buffer.from(`${env.WORKER_AUTH_USER}:${env.WORKER_AUTH_PASSWORD}`).toString("base64")}`;
}

function parseResponse(text) {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function assertStaticInventory(env, inventory) {
  if (inventory?.type !== "static") {
    throw new Error(`Inventory ${env.SEMAPHORE_INVENTORY_ID} is type "${inventory?.type}", not "static". Use a probe static inventory.`);
  }
  if (typeof inventory.inventory !== "string") {
    throw new Error("Inventory payload is not a static string blob.");
  }
}

function assertWorkerUpdateCompatible(inventory) {
  const sshKeyId = inventory.ssh_key_id ?? inventory.sshKeyId;
  if (!Number.isFinite(Number(sshKeyId))) {
    throw new Error("Inventory is missing a numeric ssh_key_id; Worker updateInventory currently requires one.");
  }
}

function assertHost(hosts, alias, expected) {
  const host = hosts.find((item) => item.alias === alias);
  if (!host) {
    throw new Error(`Expected host not found: ${alias}`);
  }
  for (const [key, value] of Object.entries(expected)) {
    if (host[key] !== value) {
      throw new Error(`Expected ${alias}.${key}=${value}, got ${host[key]}`);
    }
  }
}
