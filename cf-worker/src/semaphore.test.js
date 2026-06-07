import test from "node:test";
import assert from "node:assert/strict";
import { SemaphoreClient } from "./semaphore.js";

test("triggerTask serializes vps_task through environment and passes limit", async () => {
  const calls = [];
  const client = new SemaphoreClient({
    url: "https://semaphore.example",
    token: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return new Response(JSON.stringify({ id: 42 }), { status: 201 });
    }
  });

  const task = await client.triggerTask(1, 5, { probe: true }, { limit: "alpha" });

  assert.equal(task.id, 42);
  assert.equal(calls[0].url, "https://semaphore.example/api/project/1/tasks");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer token");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    template_id: 5,
    limit: "alpha",
    environment: "{\"vps_task\":{\"probe\":true}}"
  });
});

test("updateInventory preserves nullable and missing inventory ssh key ids", async () => {
  const calls = [];
  const client = new SemaphoreClient({
    url: "https://semaphore.example",
    token: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return new Response(null, { status: 204 });
    }
  });

  await client.updateInventory(1, {
    id: 3,
    name: "nullable-key",
    inventory: "",
    type: "static",
    ssh_key_id: null
  });
  await client.updateInventory(1, {
    id: 4,
    name: "missing-key",
    inventory: "",
    type: "static"
  });

  assert.deepEqual(JSON.parse(calls[0].init.body), {
    id: 3,
    name: "nullable-key",
    project_id: 1,
    inventory: "",
    type: "static",
    ssh_key_id: null
  });
  assert.equal(Object.hasOwn(JSON.parse(calls[1].init.body), "ssh_key_id"), false);
});

test("updateInventory refuses non-static inventories", async () => {
  const client = new SemaphoreClient({
    url: "https://semaphore.example",
    token: "token",
    fetchImpl: async () => {
      throw new Error("non-static inventory must not be sent to Semaphore");
    }
  });

  await assert.rejects(() => client.updateInventory(1, {
    id: 2,
    name: "targets-managed",
    inventory: "inventory/hosts.ini",
    type: "file"
  }), /Refusing to update non-static Semaphore inventory 2/);
});

test("deleteKey calls Semaphore key deletion endpoint", async () => {
  const calls = [];
  const client = new SemaphoreClient({
    url: "https://semaphore.example",
    token: "token",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return new Response(null, { status: 204 });
    }
  });

  await client.deleteKey(1, 7);

  assert.equal(calls[0].url, "https://semaphore.example/api/project/1/keys/7");
  assert.equal(calls[0].init.method, "DELETE");
});
