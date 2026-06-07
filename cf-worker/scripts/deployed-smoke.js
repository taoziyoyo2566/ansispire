// Deployed smoke test — hits the real workers.dev (or custom-domain) URL, NOT a
// local `worker.fetch(...)`. Its job is to catch "the deployment lags the
// working tree" (e.g. an old build without the mode selector or the root@22
// guard), which `integration:live` cannot detect because it imports the local
// handler.
//
// All checks are read-only / non-writing:
//   - GET /health           public liveness
//   - GET /vps (no auth)    expect 401 (auth is deployed)
//   - GET / (authed)        homepage HTML contains the mode-selector options
//   - POST /vps root@22     register-managed guard returns 400 *before* any
//                           Semaphore call, so nothing is written
//
// Required env:
//   WORKER_URL            e.g. https://ansispire-vps-worker.<acct>.workers.dev
//   WORKER_AUTH_USER      Basic Auth user (WORKER_AUTH_USER secret)
//   WORKER_AUTH_PASSWORD  Basic Auth password (WORKER_AUTH_PASSWORD secret)
//
// Usage:
//   WORKER_URL=https://... WORKER_AUTH_USER=... WORKER_AUTH_PASSWORD=... \
//     npm run smoke:deployed --prefix cf-worker

const ROOT22_GUARD_ERROR =
  "register-managed requires an already-managed SSH channel; root@22 belongs to onboard-bare mode";

await main().catch((err) => {
  console.error(`\nFATAL: ${err.message || err}`);
  process.exitCode = 1;
});

async function main() {
  const cfg = readConfig();
  const results = [];

  await check(results, "GET /health is public and ok", async () => {
    const res = await fetch(`${cfg.base}/health`);
    expect(res.status === 200, `expected 200, got ${res.status}`);
    const body = await res.json();
    expect(body.ok === true, `expected {ok:true}, got ${JSON.stringify(body)}`);
  });

  await check(results, "GET /vps without auth is rejected (401)", async () => {
    const res = await fetch(`${cfg.base}/vps`);
    expect(res.status === 401, `expected 401 (auth deployed), got ${res.status}`);
  });

  await check(results, "homepage exposes the create-mode selector (new wizard deployed)", async () => {
    const res = await fetch(`${cfg.base}/`, { headers: { Authorization: cfg.authHeader } });
    expect(res.status === 200, `expected 200, got ${res.status}`);
    const html = await res.text();
    expect(html.includes("Register managed node"), 'homepage missing "Register managed node" — deployment is stale');
    expect(html.includes("Onboard bare node"), 'homepage missing "Onboard bare node" — deployment is stale');
  });

  await check(results, "register-managed rejects root@22 (new guard deployed, non-writing)", async () => {
    const res = await fetch(`${cfg.base}/vps`, {
      method: "POST",
      headers: { Authorization: cfg.authHeader, "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "register-managed",
        alias: "deployed-smoke-should-never-write",
        ip: "203.0.113.10",
        port: 22,
        user: "root"
      })
    });
    expect(res.status === 400, `expected 400 from root@22 guard, got ${res.status} (deployment may be stale)`);
    const body = await res.json();
    expect(body.error === ROOT22_GUARD_ERROR, `unexpected guard error: ${JSON.stringify(body)}`);
  });

  const failed = results.filter((r) => !r.ok);
  console.log("");
  for (const r of results) {
    console.log(`${r.ok ? "PASS" : "FAIL"}  ${r.name}${r.ok ? "" : `\n      → ${r.error}`}`);
  }
  console.log(`\n${results.length - failed.length}/${results.length} checks passed against ${cfg.base}`);
  if (failed.length > 0) {
    process.exitCode = 1;
  }
}

function readConfig() {
  const base = (process.env.WORKER_URL || "").replace(/\/+$/, "");
  const user = process.env.WORKER_AUTH_USER;
  const password = process.env.WORKER_AUTH_PASSWORD;
  const missing = [
    ["WORKER_URL", base],
    ["WORKER_AUTH_USER", user],
    ["WORKER_AUTH_PASSWORD", password]
  ].filter(([, v]) => !v).map(([k]) => k);
  if (missing.length > 0) {
    throw new Error(`Missing required env vars: ${missing.join(", ")}`);
  }
  return {
    base,
    authHeader: `Basic ${Buffer.from(`${user}:${password}`).toString("base64")}`
  };
}

async function check(results, name, fn) {
  try {
    await fn();
    results.push({ name, ok: true });
  } catch (err) {
    results.push({ name, ok: false, error: err.message || String(err) });
  }
}

function expect(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}
