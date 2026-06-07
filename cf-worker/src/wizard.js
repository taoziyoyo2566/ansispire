export default String.raw`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ansispire VPS</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f7f7f4;
        color: #1f2520;
      }
      body {
        margin: 0;
      }
      main {
        display: grid;
        gap: 24px;
        max-width: 1080px;
        margin: 0 auto;
        padding: 24px;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
      }
      h1 {
        margin: 0;
        font-size: 28px;
      }
      button {
        min-height: 36px;
        border: 1px solid #1f2520;
        background: #1f2520;
        color: #fff;
        padding: 0 14px;
        border-radius: 6px;
        cursor: pointer;
      }
      button.secondary {
        background: transparent;
        color: #1f2520;
      }
      form {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        align-items: end;
      }
      .wide {
        grid-column: span 2;
      }
      .is-hidden {
        display: none;
      }
      label {
        display: grid;
        gap: 6px;
        font-size: 13px;
      }
      input, select, textarea {
        min-height: 36px;
        border: 1px solid #b7b8ad;
        border-radius: 6px;
        padding: 8px 10px;
        background: #fff;
        color: #1f2520;
        font: inherit;
      }
      textarea {
        min-height: 72px;
        resize: vertical;
      }
      .form-actions {
        display: flex;
        gap: 8px;
        align-items: center;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: #fff;
      }
      th, td {
        border-bottom: 1px solid #dedfd8;
        padding: 10px;
        text-align: left;
      }
      th {
        font-size: 12px;
        text-transform: uppercase;
        color: #586057;
      }
      .actions {
        display: flex;
        gap: 8px;
      }
      .status {
        min-height: 20px;
        font-size: 14px;
        color: #4f5d2f;
      }
      .mode {
        border-left: 4px solid #4f5d2f;
        padding: 10px 12px;
        background: #ecefe4;
        color: #283326;
        font-size: 14px;
      }
      .error {
        color: #8f1d1d;
      }
      .muted {
        color: #586057;
      }
      @media (max-width: 760px) {
        header, form {
          grid-template-columns: 1fr;
          display: grid;
        }
        table {
          display: block;
          overflow-x: auto;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Ansispire VPS</h1>
        <button class="secondary" id="refresh" type="button">Refresh</button>
      </header>
      <form id="create-form">
        <label>Mode
          <select name="mode">
            <option value="register-managed">Register managed node</option>
            <option value="onboard-bare">Onboard bare node</option>
          </select>
        </label>
        <label>Alias <input name="alias" required pattern="[A-Za-z0-9][A-Za-z0-9_.-]*"></label>
        <label>IP / Host <input name="ip" required></label>
        <label><span id="port-label">Managed port</span> <input name="port" type="number" min="1" max="65535" value="39222"></label>
        <label><span id="user-label">Managed user</span> <input name="user" value="ansible" required></label>
        <label class="onboard-only">Post-onboard managed port <input name="managed_port" type="number" min="1024" max="65535" value="39222"></label>
        <label class="onboard-only">Post-onboard managed user <input name="managed_user" value="ansible"></label>
        <label>Auth
          <select name="method">
            <option value="">Inventory only</option>
            <option value="ssh">SSH key</option>
            <option value="password">Password</option>
          </select>
        </label>
        <label>Secret <input name="secret" type="password" autocomplete="off"></label>
        <label class="wide onboard-only">Managed validation private key path <input name="managed_private_key" placeholder="~/.ssh/ansispire_ed25519"></label>
        <label class="wide onboard-only">Authorized public key paths <textarea name="authorized_keys" placeholder="~/.ssh/ansispire_ed25519.pub&#10;~/.ssh/id_ed25519.pub"></textarea></label>
        <div class="form-actions">
          <button id="submit-button" type="submit">Add VPS</button>
          <button class="secondary" id="cancel-edit" hidden type="button">Cancel</button>
        </div>
      </form>
      <div class="mode" id="mode">Checking Worker configuration...</div>
      <div class="status" id="status"></div>
      <table>
        <thead>
          <tr>
            <th>Alias</th>
            <th>Host</th>
            <th>Port</th>
            <th>User</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="hosts"></tbody>
      </table>
    </main>
    <script type="module">
      const statusEl = document.querySelector("#status");
      const hostsEl = document.querySelector("#hosts");
      const modeEl = document.querySelector("#mode");
      const form = document.querySelector("#create-form");
      const submitButton = document.querySelector("#submit-button");
      const cancelEditButton = document.querySelector("#cancel-edit");
      const portLabel = document.querySelector("#port-label");
      const userLabel = document.querySelector("#user-label");
      const onboardOnlyEls = [...document.querySelectorAll(".onboard-only")];
      const onboardModeOption = form.mode.querySelector("option[value=\"onboard-bare\"]");
      let editingAlias = "";
      let workerConfig = {
        onboardConfigured: false,
        auditConfigured: false
      };

      document.querySelector("#refresh").addEventListener("click", loadHosts);
      cancelEditButton.addEventListener("click", resetFormMode);
      form.mode.addEventListener("change", () => configureCreateMode({ preserveValues: false }));
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        submitButton.disabled = true;
        try {
          const data = Object.fromEntries(new FormData(form));
          const createMode = data.mode || "register-managed";
          const body = {
            mode: createMode,
            alias: data.alias,
            ip: data.ip,
            port: Number(data.port || defaultPortForMode(createMode)),
            user: data.user || defaultUserForMode(createMode)
          };
          if (!editingAlias && createMode === "onboard-bare") {
            Object.assign(body, buildOnboardInputs(data));
          }
          if (data.method === "ssh") {
            body.auth = { method: "ssh", private_key: data.secret };
          } else if (data.method === "password") {
            body.auth = { method: "password", password: data.secret };
          }
          const wasEditing = Boolean(editingAlias);
          const targetAlias = editingAlias || body.alias;
          let created = null;
          if (editingAlias) {
            await request("/vps/" + encodeURIComponent(editingAlias), { method: "PUT", body });
          } else {
            created = await request("/vps", { method: "POST", body });
          }
          resetFormMode();
          await loadHosts({ quiet: true });
          setStatus(wasEditing ? "Updated " + targetAlias : "Created " + created.alias + resultSuffix(created));
        } catch (err) {
          setStatus(err.message, true);
        } finally {
          submitButton.disabled = false;
        }
      });

      function applyQueryDefaults() {
        const params = new URLSearchParams(window.location.search);
        const allowed = ["mode", "alias", "ip", "port", "user", "method", "managed_port", "managed_user"];
        for (const key of allowed) {
          const value = params.get(key);
          if (value !== null && form.elements[key]) {
            form.elements[key].value = value;
          }
        }
        if (params.has("secret")) {
          setStatus("Secret query parameter ignored. Enter the secret manually; do not put passwords in URLs.", true);
        }
        if ([...params.keys()].length > 0) {
          window.history.replaceState({}, "", window.location.pathname);
        }
        configureCreateMode({ preserveValues: true });
      }

      async function loadHosts({ quiet = false } = {}) {
        const data = await request("/vps", { quiet });
        hostsEl.innerHTML = "";
        const hosts = data.hosts || [];
        if (hosts.length === 0) {
          hostsEl.innerHTML = "<tr><td class=\"muted\" colspan=\"5\">No VPS records</td></tr>";
          return;
        }
        for (const host of hosts) {
          const row = document.createElement("tr");
          row.innerHTML = [
            "<td>" + escapeHtml(host.alias) + "</td>",
            "<td>" + escapeHtml(host.ip) + "</td>",
            "<td>" + host.port + "</td>",
            "<td>" + escapeHtml(host.user) + "</td>",
            "<td class=\"actions\">" +
              "<button class=\"secondary\" data-edit=\"" + escapeHtml(host.alias) + "\" type=\"button\">Edit</button>" +
              auditButton(host.alias) +
              "<button class=\"secondary\" data-delete=\"" + escapeHtml(host.alias) + "\" type=\"button\">Remove</button>" +
            "</td>"
          ].join("");
          hostsEl.append(row);
        }
      }

      function auditButton(alias) {
        if (!workerConfig.auditConfigured) {
          return "<button class=\"secondary\" disabled title=\"SEMAPHORE_AUDIT_TEMPLATE_ID is not configured\" type=\"button\">Audit</button>";
        }
        return "<button class=\"secondary\" data-audit=\"" + escapeHtml(alias) + "\" type=\"button\">Audit</button>";
      }

      async function loadConfig() {
        workerConfig = await request("/config", { quiet: true });
        const modes = [];
        modes.push("Inventory " + workerConfig.inventoryId);
        modes.push("register-managed default");
        modes.push(workerConfig.onboardConfigured ? "onboard-bare enabled" : "onboard-bare disabled");
        modes.push(workerConfig.auditConfigured ? "audit enabled" : "audit disabled");
        modeEl.textContent = modes.join(" · ");
        syncModeAvailability();
      }

      hostsEl.addEventListener("click", async (event) => {
        const editAlias = event.target.dataset.edit;
        const auditAlias = event.target.dataset.audit;
        const deleteAlias = event.target.dataset.delete;
        if (editAlias) {
          const row = hostsEl.querySelector("[data-edit=\"" + cssEscape(editAlias) + "\"]").closest("tr");
          startEdit({
            alias: editAlias,
            ip: row.children[1].textContent,
            port: row.children[2].textContent,
            user: row.children[3].textContent
          });
        }
        if (auditAlias) {
          try {
            const result = await request("/vps/" + encodeURIComponent(auditAlias) + "/audit", { method: "POST" });
            setStatus("Audit task triggered: " + result.taskId);
          } catch (err) {
            setStatus(err.message, true);
          }
        }
        if (deleteAlias) {
          try {
            await request("/vps/" + encodeURIComponent(deleteAlias), { method: "DELETE" });
            await loadHosts({ quiet: true });
            setStatus("Removed " + deleteAlias);
          } catch (err) {
            setStatus(err.message, true);
          }
        }
      });

      function buildOnboardInputs(data) {
        return {
          managed_port: Number(data.managed_port || 39222),
          managed_user: data.managed_user || "ansible",
          managed_private_key: data.managed_private_key || "",
          authorized_keys: String(data.authorized_keys || "")
            .split(/\r?\n/)
            .map((item) => item.trim())
            .filter(Boolean)
            .map((public_key) => ({ public_key }))
        };
      }

      function startEdit(host) {
        editingAlias = host.alias;
        form.alias.value = host.alias;
        form.alias.disabled = true;
        form.mode.value = "register-managed";
        form.mode.disabled = true;
        form.ip.value = host.ip;
        form.port.value = host.port;
        form.user.value = host.user;
        form.method.value = "";
        form.secret.value = "";
        submitButton.textContent = "Update VPS";
        cancelEditButton.hidden = false;
        configureCreateMode({ preserveValues: true });
        setStatus("Editing " + host.alias + ". Auth and onboard-only fields are ignored for updates.");
      }

      function resetFormMode() {
        editingAlias = "";
        form.reset();
        form.alias.disabled = false;
        form.mode.disabled = false;
        form.mode.value = "register-managed";
        form.managed_port.value = 39222;
        form.managed_user.value = "ansible";
        configureCreateMode({ preserveValues: false });
        submitButton.textContent = "Add VPS";
        cancelEditButton.hidden = true;
      }

      function configureCreateMode({ preserveValues = true } = {}) {
        const mode = form.mode.value || "register-managed";
        const isOnboard = mode === "onboard-bare";
        portLabel.textContent = isOnboard ? "Bootstrap port" : "Managed port";
        userLabel.textContent = isOnboard ? "Bootstrap user" : "Managed user";
        for (const element of onboardOnlyEls) {
          element.classList.toggle("is-hidden", !isOnboard);
          for (const field of element.querySelectorAll("input, textarea, select")) {
            field.disabled = !isOnboard;
          }
        }
        if (!preserveValues) {
          form.port.value = defaultPortForMode(mode);
          form.user.value = defaultUserForMode(mode);
          form.method.value = isOnboard ? "password" : "";
          form.secret.value = "";
        }
      }

      function syncModeAvailability() {
        onboardModeOption.disabled = !workerConfig.onboardConfigured;
        if (!workerConfig.onboardConfigured && form.mode.value === "onboard-bare") {
          form.mode.value = "register-managed";
          configureCreateMode({ preserveValues: false });
        }
      }

      function defaultPortForMode(mode) {
        return mode === "onboard-bare" ? 22 : 39222;
      }

      function defaultUserForMode(mode) {
        return mode === "onboard-bare" ? "root" : "ansible";
      }

      async function request(path, options = {}) {
        if (!options.quiet) {
          setStatus("Working...");
        }
        const init = { method: options.method || "GET" };
        if (options.body) {
          init.headers = { "Content-Type": "application/json" };
          init.body = JSON.stringify(options.body);
        }
        const response = await fetch(path, init);
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || "Request failed");
        }
        if (!options.quiet) {
          setStatus("Ready");
        }
        return data;
      }

      function setStatus(message, isError = false) {
        statusEl.textContent = message;
        statusEl.classList.toggle("error", isError);
      }

      function resultSuffix(created) {
        if (created.taskId) {
          return " and triggered onboard task " + created.taskId;
        }
        if (created.mode === "register-managed") {
          return " as a managed inventory record";
        }
        return "; onboard task did not return an id";
      }

      function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, (char) => ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        }[char]));
      }

      function cssEscape(value) {
        if (window.CSS && typeof window.CSS.escape === "function") {
          return window.CSS.escape(value);
        }
        return String(value).replace(/["\\]/g, "\\$&");
      }

      configureCreateMode({ preserveValues: false });
      applyQueryDefaults();
      Promise.all([loadConfig(), loadHosts({ quiet: Boolean(statusEl.textContent) })]).catch((err) => {
        setStatus(err.message, true);
        hostsEl.innerHTML = "<tr><td class=\"error\" colspan=\"5\">Unable to load VPS records</td></tr>";
      });
    </script>
  </body>
</html>`;
