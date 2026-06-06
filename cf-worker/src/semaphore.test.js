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
