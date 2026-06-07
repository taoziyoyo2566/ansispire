import { IttyRouter, error, html, json, withParams } from "itty-router";
import {
  findHost,
  listHosts,
  normalizeAlias,
  normalizeHost,
  removeHost,
  upsertHost
} from "./inventory.js";
import { SemaphoreClient, SemaphoreError } from "./semaphore.js";
import wizardHtml from "./wizard.js";

const router = IttyRouter();

router
  .all("*", withParams)
  .get("/", () => html(wizardHtml))
  .get("/health", () => json({ ok: true }))
  .get("/config", (_request, env) => {
    const cfg = context(env);
    return json({
      projectId: cfg.projectId,
      inventoryId: cfg.inventoryId,
      onboardConfigured: Boolean(cfg.onboardTemplateId),
      auditConfigured: Boolean(cfg.auditTemplateId)
    });
  })
  .get("/vps", async (_request, env) => {
    const ctx = context(env);
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    const inventoryError = validateStaticInventory(inventory);
    if (inventoryError) {
      return inventoryError;
    }
    return json({ hosts: listHosts(inventory.inventory) });
  })
  .post("/vps", async (request, env) => {
    const ctx = context(env);
    const input = await readJson(request);
    const mode = normalizeCreateMode(input.mode);
    if (mode.error) {
      return json({ error: mode.error }, { status: 400 });
    }
    const modeValidationError = validateCreateMode(mode.value, ctx, input);
    if (modeValidationError) {
      return json({ error: modeValidationError }, { status: 412 });
    }
    const validationError = validateAuth(input.auth);
    if (validationError) {
      return json({ error: validationError }, { status: 400 });
    }
    const onboardValidationError = mode.value === "onboard-bare" ? validateOnboardInput(input) : "";
    if (onboardValidationError) {
      return json({ error: onboardValidationError }, { status: 400 });
    }
    const host = tryNormalize(() => buildInventoryHost(input, mode.value));
    if (host.error) {
      return json({ error: host.error }, { status: 400 });
    }
    const hostModeError = validateInventoryHostMode(mode.value, host.value);
    if (hostModeError) {
      return json({ error: hostModeError }, { status: 400 });
    }
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    const inventoryError = validateStaticInventory(inventory);
    if (inventoryError) {
      return inventoryError;
    }
    if (findHost(inventory.inventory, host.value.alias)) {
      return json({ error: "alias already exists" }, { status: 409 });
    }

    const key = await maybeCreateKey(ctx, input, host.value.alias, host.value.user);
    const keyId = key?.id;
    const nextInventory = upsertHost(inventory.inventory, { ...host.value, keyId });
    try {
      await ctx.client.updateInventory(ctx.projectId, {
        ...inventory,
        inventory: nextInventory
      });
    } catch (err) {
      if (keyId) {
        await safeDeleteKey(ctx, keyId);
      }
      throw err;
    }

    let taskId = null;
    if (mode.value === "onboard-bare") {
      const task = await ctx.client.triggerTask(
        ctx.projectId,
        ctx.onboardTemplateId,
        buildOnboardTask(input, host.value, keyId),
        { limit: host.value.alias }
      );
      taskId = task?.id || null;
    }

    return json({ alias: host.value.alias, mode: mode.value, keyId: keyId || null, taskId }, { status: 201 });
  })
  .put("/vps/:alias", async (request, env) => {
    const ctx = context(env);
    const alias = tryNormalize(() => normalizeAlias(request.alias));
    if (alias.error) {
      return json({ error: alias.error }, { status: 400 });
    }
    const input = await readJson(request);
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    const inventoryError = validateStaticInventory(inventory);
    if (inventoryError) {
      return inventoryError;
    }
    const existing = findHost(inventory.inventory, alias.value);
    if (!existing) {
      return json({ error: "alias not found" }, { status: 404 });
    }
    const nextHost = tryNormalize(() => normalizeHost({ ...existing, ...input, alias: alias.value }));
    if (nextHost.error) {
      return json({ error: nextHost.error }, { status: 400 });
    }
    const nextInventory = upsertHost(inventory.inventory, nextHost.value);
    await ctx.client.updateInventory(ctx.projectId, {
      ...inventory,
      inventory: nextInventory
    });
    return json({ ok: true });
  })
  .delete("/vps/:alias", async (request, env) => {
    const ctx = context(env);
    const alias = tryNormalize(() => normalizeAlias(request.alias));
    if (alias.error) {
      return json({ error: alias.error }, { status: 400 });
    }
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    const inventoryError = validateStaticInventory(inventory);
    if (inventoryError) {
      return inventoryError;
    }
    let nextInventory;
    try {
      nextInventory = removeHost(inventory.inventory, alias.value);
    } catch {
      return json({ error: "alias not found" }, { status: 404 });
    }
    await ctx.client.updateInventory(ctx.projectId, {
      ...inventory,
      inventory: nextInventory
    });
    return json({ ok: true });
  })
  .post("/vps/:alias/audit", async (request, env) => {
    const ctx = context(env);
    if (!ctx.auditTemplateId) {
      return json({ error: "SEMAPHORE_AUDIT_TEMPLATE_ID is not configured" }, { status: 412 });
    }
    const alias = tryNormalize(() => normalizeAlias(request.alias));
    if (alias.error) {
      return json({ error: alias.error }, { status: 400 });
    }
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    const inventoryError = validateStaticInventory(inventory);
    if (inventoryError) {
      return inventoryError;
    }
    if (!findHost(inventory.inventory, alias.value)) {
      return json({ error: "alias not found" }, { status: 404 });
    }
    const task = await ctx.client.triggerTask(ctx.projectId, ctx.auditTemplateId, {
      checks: {},
      target: alias.value
    }, {
      limit: alias.value
    });
    return json({ taskId: task?.id || null }, { status: 202 });
  })
  .all("*", () => json({ error: "not found" }, { status: 404 }));

export default {
  fetch: async (request, env, executionContext) => {
    const authFailure = await requireBasicAuth(request, env);
    if (authFailure) {
      return authFailure;
    }
    return router
      .fetch(request, env, executionContext)
      .catch((err) => {
        if (err instanceof HttpError) {
          return json({ error: err.message }, { status: err.status });
        }
        if (err instanceof SemaphoreError) {
          return json({ error: "Semaphore API request failed", upstreamStatus: err.status }, { status: 502 });
        }
        return error(500, err.message || "internal error");
      });
  }
};

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "HttpError";
    this.status = status;
  }
}

function context(env) {
  return {
    projectId: requiredEnv(env, "SEMAPHORE_PROJECT_ID"),
    inventoryId: requiredEnv(env, "SEMAPHORE_INVENTORY_ID"),
    onboardTemplateId: optionalNumberEnv(env, "SEMAPHORE_ONBOARD_TEMPLATE_ID"),
    auditTemplateId: optionalNumberEnv(env, "SEMAPHORE_AUDIT_TEMPLATE_ID"),
    client: new SemaphoreClient({
      url: requiredEnv(env, "SEMAPHORE_URL"),
      token: requiredEnv(env, "SEMAPHORE_API_TOKEN")
    })
  };
}

async function readJson(request) {
  try {
    return await request.json();
  } catch {
    throw new HttpError(400, "request body must be valid JSON");
  }
}

async function safeDeleteKey(ctx, keyId) {
  try {
    await ctx.client.deleteKey(ctx.projectId, keyId);
  } catch {
    // Best-effort compensation; preserve the original failure response.
  }
}

async function requireBasicAuth(request, env) {
  const pathname = new URL(request.url).pathname;
  if (pathname === "/health") {
    return null;
  }

  const expectedUser = requiredAuthEnv(env, "WORKER_AUTH_USER");
  const expectedPassword = requiredAuthEnv(env, "WORKER_AUTH_PASSWORD");
  if (!expectedUser || !expectedPassword) {
    return json({ error: "Worker authentication is not configured" }, { status: 503 });
  }

  const credentials = parseBasicCredentials(request.headers.get("Authorization"));
  if (!credentials) {
    return unauthorized();
  }

  const [userOk, passwordOk] = await Promise.all([
    constantTimeEqual(credentials.user, expectedUser),
    constantTimeEqual(credentials.password, expectedPassword)
  ]);
  if (!userOk || !passwordOk) {
    return unauthorized();
  }

  return null;
}

function requiredAuthEnv(env, key) {
  const value = env?.[key];
  if (value === undefined || value === null || String(value).trim() === "") {
    return "";
  }
  return String(value);
}

function parseBasicCredentials(header) {
  if (!header) {
    return null;
  }
  const [scheme, token] = header.split(/\s+/, 2);
  if (scheme?.toLowerCase() !== "basic" || !token) {
    return null;
  }
  let decoded;
  try {
    decoded = atob(token);
  } catch {
    return null;
  }
  const separator = decoded.indexOf(":");
  if (separator < 0) {
    return null;
  }
  return {
    user: decoded.slice(0, separator),
    password: decoded.slice(separator + 1)
  };
}

async function constantTimeEqual(actual, expected) {
  const encoder = new TextEncoder();
  const [actualHash, expectedHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(actual)),
    crypto.subtle.digest("SHA-256", encoder.encode(expected))
  ]);
  const actualBytes = new Uint8Array(actualHash);
  const expectedBytes = new Uint8Array(expectedHash);
  let diff = actualBytes.length ^ expectedBytes.length;
  for (let i = 0; i < Math.max(actualBytes.length, expectedBytes.length); i += 1) {
    diff |= (actualBytes[i] || 0) ^ (expectedBytes[i] || 0);
  }
  return diff === 0;
}

function unauthorized() {
  return json({ error: "authentication required" }, {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Ansispire VPS", charset="UTF-8"'
    }
  });
}

async function maybeCreateKey(ctx, input, alias, login) {
  const auth = input.auth || {};
  if (auth.method === "ssh") {
    return ctx.client.createKey(ctx.projectId, {
      name: `vps:${alias}:ssh`,
      type: "ssh",
      login,
      privateKey: auth.private_key,
      passphrase: auth.passphrase || ""
    });
  }
  if (auth.method === "password") {
    return ctx.client.createKey(ctx.projectId, {
      name: `vps:${alias}:password`,
      type: "login_password",
      login,
      password: auth.password
    });
  }
  return null;
}

function normalizeCreateMode(mode) {
  const value = String(mode || "register-managed").trim();
  if (["register-managed", "onboard-bare"].includes(value)) {
    return { value };
  }
  return { error: "mode must be register-managed or onboard-bare" };
}

function validateCreateMode(mode, ctx) {
  if (mode === "onboard-bare" && !ctx.onboardTemplateId) {
    return "SEMAPHORE_ONBOARD_TEMPLATE_ID is required for onboard-bare mode";
  }
  return "";
}

function validateInventoryHostMode(mode, host) {
  if (mode === "register-managed" && host.user === "root" && host.port === 22) {
    return "register-managed requires an already-managed SSH channel; root@22 belongs to onboard-bare mode";
  }
  return "";
}

function buildInventoryHost(input, mode) {
  if (mode === "onboard-bare") {
    return normalizeHost({
      alias: input.alias,
      ip: input.ip,
      port: input.bootstrap_port || input.bootstrapPort || input.port || 22,
      user: input.bootstrap_user || input.bootstrapUser || input.user || "root",
      vars: {
        lifecycle_state: "onboarding",
        lifecycle_mode: "onboard-bare"
      }
    });
  }

  return normalizeHost({
    alias: input.alias,
    ip: input.ip,
    port: input.managed_port || input.managedPort || input.port || 39222,
    user: input.managed_user || input.managedUser || input.user || "ansible",
    vars: {
      lifecycle_state: "managed",
      lifecycle_mode: "register-managed"
    }
  });
}

function validateAuth(auth = {}) {
  if (!auth.method) {
    return "";
  }
  if (auth.method === "ssh" && !auth.private_key) {
    return "auth.private_key is required when auth.method is ssh";
  }
  if (auth.method === "password" && !auth.password) {
    return "auth.password is required when auth.method is password";
  }
  if (!["ssh", "password"].includes(auth.method)) {
    return "auth.method must be ssh or password";
  }
  return "";
}

function validateOnboardInput(input = {}) {
  if (!String(input.managed_private_key || input.managedPrivateKey || "").trim()) {
    return "managed_private_key is required when SEMAPHORE_ONBOARD_TEMPLATE_ID is configured";
  }
  return "";
}

function tryNormalize(fn) {
  try {
    return { value: fn() };
  } catch (err) {
    return { error: err.message };
  }
}

function validateStaticInventory(inventory) {
  if (inventory?.type === "static" && typeof inventory.inventory === "string") {
    return null;
  }
  return json({
    error: "Configured Semaphore inventory must be type static for Worker VPS operations",
    inventoryId: inventory?.id ?? null,
    inventoryType: inventory?.type ?? null
  }, { status: 412 });
}

function buildOnboardTask(input, host, keyId) {
  const auth = input.auth || {};
  const managedPort = Number(input.managed_port || input.managedPort || 39222);
  const managedUser = input.managed_user || input.managedUser || "ansible";
  return {
    bootstrap: {
      host: host.ip,
      port: Number(input.bootstrap_port || input.bootstrapPort || input.port || 22),
      user: input.bootstrap_user || input.bootstrapUser || input.user || "root",
      auth: {
        method: auth.method || "ssh",
        key_id: keyId || null
      }
    },
    managed: {
      user: managedUser,
      groups: input.managed_groups || ["sudo", "ssh-users"],
      shell: input.managed_shell || "/bin/bash",
      authorized_keys: input.authorized_keys || [],
      ansible_key: {
        private_key: input.managed_private_key || input.managedPrivateKey || ""
      },
      sudo: {
        nopasswd: true
      }
    },
    ssh: {
      managed_port: managedPort,
      disable_root_login: true,
      disable_password_login: true,
      disable_kbd_interactive: true,
      allow_groups: ["ssh-users"],
      close_bootstrap_port_after_success: true
    },
    profile: {
      base_packages: true,
      unattended_upgrades: true,
      system_limits: true
    },
    packages: {
      install: input.packages?.install || [],
      remove: input.packages?.remove || []
    },
    firewall: {
      allowed_tcp_ports: [managedPort]
    },
    fail2ban: {
      enabled: true
    }
  };
}

function requiredEnv(env, key) {
  const value = env?.[key];
  if (value === undefined || value === null || String(value).trim() === "") {
    throw new Error(`${key} is required`);
  }
  return String(value);
}

function optionalNumberEnv(env, key) {
  const value = env?.[key];
  if (value === undefined || value === null || String(value).trim() === "") {
    return null;
  }
  return Number(value);
}
