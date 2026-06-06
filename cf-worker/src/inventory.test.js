import test from "node:test";
import assert from "node:assert/strict";
import {
  findHost,
  listHosts,
  parseInventory,
  removeHost,
  serializeInventory,
  upsertHost
} from "./inventory.js";

const SAMPLE = `[vps_targets]
alpha ansible_host=203.0.113.10 ansible_port=1156 ansible_user=ansible ansible_ssh_private_key_id=7

[vps_targets:vars]
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args="-o StrictHostKeyChecking=accept-new"
`;

test("parseInventory extracts target hosts and vars", () => {
  const parsed = parseInventory(SAMPLE);
  assert.deepEqual(parsed.hosts, [
    {
      alias: "alpha",
      ip: "203.0.113.10",
      port: 1156,
      user: "ansible",
      keyId: 7
    }
  ]);
  assert.equal(parsed.groupVars.ansible_python_interpreter, "/usr/bin/python3");
});

test("serializeInventory writes stable vps_targets inventory", () => {
  const text = serializeInventory({
    hosts: [{ alias: "beta", ip: "203.0.113.11", port: 2222, user: "ansible", keyId: 9 }]
  });
  assert.match(text, /\[vps_targets]/);
  assert.match(text, /beta ansible_host=203\.0\.113\.11 ansible_port=2222 ansible_user=ansible ansible_ssh_private_key_id=9/);
  assert.match(text, /\[vps_targets:vars]/);
});

test("upsertHost adds and updates a host", () => {
  const added = upsertHost("", {
    alias: "gamma",
    ip: "203.0.113.12",
    port: 1156,
    user: "ansible",
    keyId: 10
  });
  assert.equal(findHost(added, "gamma").ip, "203.0.113.12");

  const updated = upsertHost(added, {
    alias: "gamma",
    ip: "203.0.113.13",
    port: 1157,
    user: "deployer",
    keyId: 10
  });
  assert.deepEqual(listHosts(updated), [
    {
      alias: "gamma",
      ip: "203.0.113.13",
      port: 1157,
      user: "deployer",
      keyId: 10
    }
  ]);
});

test("removeHost deletes a host and reports missing alias", () => {
  const withoutAlpha = removeHost(SAMPLE, "alpha");
  assert.equal(findHost(withoutAlpha, "alpha"), null);
  assert.throws(() => removeHost(withoutAlpha, "alpha"), /alias not found/);
});

test("upsertHost validates aliases and port ranges", () => {
  assert.throws(() => upsertHost("", { alias: "../bad", ip: "127.0.0.1", port: 22, user: "root" }), /alias/);
  assert.throws(() => upsertHost("", { alias: "ok", ip: "127.0.0.1", port: 70000, user: "root" }), /port/);
});
