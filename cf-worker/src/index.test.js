import test from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

const AUTH_HEADER = `Basic ${Buffer.from("operator:local-password").toString("base64")}`;

function testEnv(overrides = {}) {
  return {
    SEMAPHORE_URL: "https://semaphore.example",
    SEMAPHORE_PROJECT_ID: "1",
    SEMAPHORE_INVENTORY_ID: "3",
    SEMAPHORE_ONBOARD_TEMPLATE_ID: "",
    SEMAPHORE_AUDIT_TEMPLATE_ID: "",
    SEMAPHORE_API_TOKEN: "secret-token",
    WORKER_AUTH_USER: "operator",
    WORKER_AUTH_PASSWORD: "local-password",
    ...overrides
  };
}

function authHeaders(headers = {}) {
  return {
    Authorization: AUTH_HEADER,
    ...headers
  };
}

test("GET /health remains public for uptime checks", async () => {
  const response = await worker.fetch(new Request("https://worker.local/health"), {});

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true });
});

test("protected routes require Basic Auth", async () => {
  const missing = await worker.fetch(new Request("https://worker.local/vps"), testEnv());
  assert.equal(missing.status, 401);
  assert.equal(missing.headers.get("WWW-Authenticate"), 'Basic realm="Ansispire VPS", charset="UTF-8"');
  assert.deepEqual(await missing.json(), { error: "authentication required" });

  const wrong = await worker.fetch(new Request("https://worker.local/vps", {
    headers: {
      Authorization: `Basic ${Buffer.from("operator:wrong").toString("base64")}`
    }
  }), testEnv());
  assert.equal(wrong.status, 401);
});

test("protected routes fail closed when auth secrets are not configured", async () => {
  const response = await worker.fetch(new Request("https://worker.local/vps"), {
    SEMAPHORE_URL: "https://semaphore.example",
    SEMAPHORE_PROJECT_ID: "1",
    SEMAPHORE_INVENTORY_ID: "3",
    SEMAPHORE_ONBOARD_TEMPLATE_ID: "",
    SEMAPHORE_AUDIT_TEMPLATE_ID: "",
    SEMAPHORE_API_TOKEN: "secret-token"
  });

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: "Worker authentication is not configured" });
});

test("GET /config returns non-sensitive Worker configuration state", async () => {
  const response = await worker.fetch(new Request("https://worker.local/config", {
    headers: authHeaders()
  }), testEnv({
    SEMAPHORE_AUDIT_TEMPLATE_ID: "9"
  }));

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    projectId: "1",
    inventoryId: "3",
    onboardConfigured: false,
    auditConfigured: true
  });
});

test("GET /vps rejects non-static inventories instead of returning an empty list", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    assert.equal(init.method, "GET");
    assert.equal(url, "https://semaphore.example/api/project/1/inventory/3");
    return new Response(JSON.stringify({
      id: 3,
      name: "targets-managed",
      type: "file",
      inventory: "inventory/hosts.ini"
    }), { status: 200 });
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      headers: authHeaders()
    }), testEnv());

    assert.equal(response.status, 412);
    assert.deepEqual(await response.json(), {
      error: "Configured Semaphore inventory must be type static for Worker VPS operations",
      inventoryId: 3,
      inventoryType: "file"
    });
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps rejects non-static inventories before writing", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({
      id: 3,
      name: "targets-managed",
      type: "file",
      inventory: "inventory/hosts.ini"
    }), { status: 200 });
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        alias: "alpha",
        ip: "203.0.113.10"
      })
    }), testEnv());

    assert.equal(response.status, 412);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].init.method, "GET");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps register-managed writes the managed channel and does not trigger onboard", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith("/inventory/3") && init.method === "GET") {
      return new Response(JSON.stringify({
        id: 3,
        name: "probe",
        type: "static",
        ssh_key_id: 2,
        inventory: "[vps_targets]\n\n[vps_targets:vars]\nansible_python_interpreter=/usr/bin/python3\n"
      }), { status: 200 });
    }
    if (String(url).endsWith("/inventory/3") && init.method === "PUT") {
      return new Response(null, { status: 204 });
    }
    throw new Error(`unexpected request: ${init.method} ${url}`);
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        mode: "register-managed",
        alias: "alpha",
        ip: "203.0.113.10",
        port: 22,
        user: "root",
        managed_port: 39222,
        managed_user: "ansible"
      })
    }), testEnv({
      SEMAPHORE_ONBOARD_TEMPLATE_ID: "8"
    }));

    assert.equal(response.status, 201);
    assert.deepEqual(await response.json(), {
      alias: "alpha",
      mode: "register-managed",
      keyId: null,
      taskId: null
    });
    assert.equal(calls.length, 2);
    const updateBody = JSON.parse(calls[1].init.body);
    assert.match(updateBody.inventory, /alpha .*ansible_port=39222/);
    assert.match(updateBody.inventory, /alpha .*ansible_user=ansible/);
    assert.match(updateBody.inventory, /alpha .*lifecycle_state=managed/);
    assert.match(updateBody.inventory, /alpha .*lifecycle_mode=register-managed/);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps register-managed defaults to ansible on port 39222", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith("/inventory/3") && init.method === "GET") {
      return new Response(JSON.stringify({
        id: 3,
        name: "probe",
        type: "static",
        ssh_key_id: 2,
        inventory: "[vps_targets]\n"
      }), { status: 200 });
    }
    if (String(url).endsWith("/inventory/3") && init.method === "PUT") {
      return new Response(null, { status: 204 });
    }
    throw new Error(`unexpected request: ${init.method} ${url}`);
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        alias: "alpha",
        ip: "203.0.113.10"
      })
    }), testEnv());

    assert.equal(response.status, 201);
    const updateBody = JSON.parse(calls[1].init.body);
    assert.match(updateBody.inventory, /alpha .*ansible_port=39222/);
    assert.match(updateBody.inventory, /alpha .*ansible_user=ansible/);
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps register-managed rejects accidental root port 22 records", async () => {
  const response = await worker.fetch(new Request("https://worker.local/vps", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      mode: "register-managed",
      alias: "alpha",
      ip: "203.0.113.10",
      port: 22,
      user: "root"
    })
  }), testEnv());

  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), {
    error: "register-managed requires an already-managed SSH channel; root@22 belongs to onboard-bare mode"
  });
});

test("POST /vps onboard-bare requires an onboard template", async () => {
  const response = await worker.fetch(new Request("https://worker.local/vps", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      mode: "onboard-bare",
      alias: "alpha",
      ip: "203.0.113.10",
      port: 22,
      user: "root"
    })
  }), testEnv());

  assert.equal(response.status, 412);
  assert.deepEqual(await response.json(), {
    error: "SEMAPHORE_ONBOARD_TEMPLATE_ID is required for onboard-bare mode"
  });
});

test("POST /vps rejects onboard requests missing the managed validation key path", async () => {
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("Semaphore should not be called for invalid onboard input");
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        mode: "onboard-bare",
        alias: "alpha",
        ip: "203.0.113.10",
        port: 22,
        user: "root",
        auth: { method: "password", password: "bootstrap-password" }
      })
    }), testEnv({
      SEMAPHORE_ONBOARD_TEMPLATE_ID: "8"
    }));

    assert.equal(response.status, 400);
    assert.deepEqual(await response.json(), {
      error: "managed_private_key is required when SEMAPHORE_ONBOARD_TEMPLATE_ID is configured"
    });
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps reports invalid JSON as a client error", async () => {
  const response = await worker.fetch(new Request("https://worker.local/vps", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: "{"
  }), testEnv());

  assert.equal(response.status, 400);
  assert.deepEqual(await response.json(), {
    error: "request body must be valid JSON"
  });
});

test("POST /vps/:alias/audit checks configuration and inventory before triggering", async () => {
  const missingConfig = await worker.fetch(new Request("https://worker.local/vps/missing/audit", {
    method: "POST",
    headers: authHeaders()
  }), testEnv());
  assert.equal(missingConfig.status, 412);

  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({
      id: 3,
      name: "probe",
      type: "static",
      ssh_key_id: 2,
      inventory: "[vps_targets]\n\n[vps_targets:vars]\nansible_python_interpreter=/usr/bin/python3\n"
    }), { status: 200 });
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps/missing/audit", {
      method: "POST",
      headers: authHeaders()
    }), testEnv({
      SEMAPHORE_AUDIT_TEMPLATE_ID: "9"
    }));

    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: "alias not found" });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "https://semaphore.example/api/project/1/inventory/3");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps deletes a newly-created key when inventory update fails", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith("/inventory/3") && init.method === "GET") {
      return new Response(JSON.stringify({
        id: 3,
        name: "probe",
        type: "static",
        ssh_key_id: 2,
        inventory: "[vps_targets]\n\n[vps_targets:vars]\nansible_python_interpreter=/usr/bin/python3\n"
      }), { status: 200 });
    }
    if (String(url).endsWith("/keys") && init.method === "POST") {
      return new Response(JSON.stringify({ id: 7 }), { status: 201 });
    }
    if (String(url).endsWith("/inventory/3") && init.method === "PUT") {
      return new Response(JSON.stringify({ error: "upstream inventory failure" }), { status: 500 });
    }
    if (String(url).endsWith("/keys/7") && init.method === "DELETE") {
      return new Response("", { status: 204 });
    }
    throw new Error(`unexpected request: ${init.method} ${url}`);
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        alias: "alpha",
        ip: "203.0.113.10",
        port: 39222,
        user: "ansible",
        auth: { method: "password", password: "bootstrap-password" }
      })
    }), testEnv());

    assert.equal(response.status, 502);
    assert.deepEqual(await response.json(), {
      error: "Semaphore API request failed",
      upstreamStatus: 500
    });
    assert.equal(calls.at(-1).url, "https://semaphore.example/api/project/1/keys/7");
    assert.equal(calls.at(-1).init.method, "DELETE");
  } finally {
    globalThis.fetch = previousFetch;
  }
});

test("POST /vps onboard-bare carries camelCase managedPrivateKey into the onboard payload", async () => {
  const calls = [];
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    if (String(url).endsWith("/inventory/3") && init.method === "GET") {
      return new Response(JSON.stringify({
        id: 3,
        name: "probe",
        type: "static",
        ssh_key_id: 2,
        inventory: "[vps_targets]\n"
      }), { status: 200 });
    }
    if (String(url).endsWith("/inventory/3") && init.method === "PUT") {
      return new Response(null, { status: 204 });
    }
    if (String(url).endsWith("/tasks") && init.method === "POST") {
      return new Response(JSON.stringify({ id: 99 }), { status: 201 });
    }
    throw new Error(`unexpected request: ${init.method} ${url}`);
  };

  try {
    const response = await worker.fetch(new Request("https://worker.local/vps", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        mode: "onboard-bare",
        alias: "alpha",
        ip: "203.0.113.10",
        port: 22,
        user: "root",
        managedPrivateKey: "~/.ssh/ansispire_ed25519"
      })
    }), testEnv({
      SEMAPHORE_ONBOARD_TEMPLATE_ID: "8"
    }));

    assert.equal(response.status, 201);
    const taskCall = calls.find((c) => String(c.url).endsWith("/tasks") && c.init.method === "POST");
    assert.ok(taskCall, "onboard-bare should trigger the onboard task");
    const vpsTask = JSON.parse(JSON.parse(taskCall.init.body).environment).vps_task;
    assert.equal(vpsTask.managed.ansible_key.private_key, "~/.ssh/ansispire_ed25519");
  } finally {
    globalThis.fetch = previousFetch;
  }
});
