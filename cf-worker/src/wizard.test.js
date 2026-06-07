import test from "node:test";
import assert from "node:assert/strict";
import wizardHtml from "./wizard.js";

test("wizard inline script parses as JavaScript", () => {
  const match = wizardHtml.match(/<script type="module">([\s\S]+)<\/script>/);
  assert.ok(match, "wizard module script should exist");
  assert.doesNotThrow(() => new Function(match[1]));
});

test("wizard form does not leak secrets through query submission", () => {
  assert.match(wizardHtml, /event\.preventDefault\(\)/);
  assert.match(wizardHtml, /Secret query parameter ignored/);
});

test("wizard exposes browser management controls and config-aware audit state", () => {
  assert.match(wizardHtml, /Update VPS/);
  assert.match(wizardHtml, /data-edit/);
  assert.match(wizardHtml, /SEMAPHORE_AUDIT_TEMPLATE_ID is not configured/);
  assert.match(wizardHtml, /Register managed node/);
  assert.match(wizardHtml, /Onboard bare node/);
  assert.match(wizardHtml, /onboard-bare disabled/);
});
