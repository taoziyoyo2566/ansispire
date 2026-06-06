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
  .get("/vps", async (_request, env) => {
    const ctx = context(env);
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    return json({ hosts: listHosts(inventory.inventory) });
  })
  .post("/vps", async (request, env) => {
    const ctx = context(env);
    const input = await readJson(request);
    const validationError = validateAuth(input.auth);
    if (validationError) {
      return json({ error: validationError }, { status: 400 });
    }
    const host = tryNormalize(() => normalizeHost(input));
    if (host.error) {
      return json({ error: host.error }, { status: 400 });
    }
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
    if (findHost(inventory.inventory, host.value.alias)) {
      return json({ error: "alias already exists" }, { status: 409 });
    }

    const key = await maybeCreateKey(ctx, input, host.value.alias);
    const keyId = key?.id;
    const nextInventory = upsertHost(inventory.inventory, { ...host.value, keyId });
    await ctx.client.updateInventory(ctx.projectId, {
      ...inventory,
      inventory: nextInventory
    });

    let taskId = null;
    if (ctx.onboardTemplateId) {
      const task = await ctx.client.triggerTask(
        ctx.projectId,
        ctx.onboardTemplateId,
        buildOnboardTask(input, host.value, keyId),
        { limit: host.value.alias }
      );
      taskId = task?.id || null;
    }

    return json({ alias: host.value.alias, keyId: keyId || null, taskId }, { status: 201 });
  })
  .put("/vps/:alias", async (request, env) => {
    const ctx = context(env);
    const alias = tryNormalize(() => normalizeAlias(request.alias));
    if (alias.error) {
      return json({ error: alias.error }, { status: 400 });
    }
    const input = await readJson(request);
    const inventory = await ctx.client.getInventory(ctx.projectId, ctx.inventoryId);
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
      return json({ error: "SEMAPHORE_AUDIT_TEMPLATE_ID is not configured" }, { status: 500 });
    }
    const alias = tryNormalize(() => normalizeAlias(request.alias));
    if (alias.error) {
      return json({ error: alias.error }, { status: 400 });
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
  fetch: (request, env, executionContext) =>
    router
      .fetch(request, env, executionContext)
      .catch((err) => {
        if (err instanceof SemaphoreError) {
          return json({ error: err.message }, { status: 502 });
        }
        return error(500, err.message || "internal error");
      })
};

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
    throw new Error("request body must be valid JSON");
  }
}

async function maybeCreateKey(ctx, input, alias) {
  const auth = input.auth || {};
  if (auth.method === "ssh") {
    return ctx.client.createKey(ctx.projectId, {
      name: `vps:${alias}:ssh`,
      type: "ssh",
      login: input.user || "root",
      privateKey: auth.private_key,
      passphrase: auth.passphrase || ""
    });
  }
  if (auth.method === "password") {
    return ctx.client.createKey(ctx.projectId, {
      name: `vps:${alias}:password`,
      type: "login_password",
      login: input.user || "root",
      password: auth.password
    });
  }
  return null;
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

function tryNormalize(fn) {
  try {
    return { value: fn() };
  } catch (err) {
    return { error: err.message };
  }
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
        private_key: input.managed_private_key || ""
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
