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
      label {
        display: grid;
        gap: 6px;
        font-size: 13px;
      }
      input, select {
        min-height: 36px;
        border: 1px solid #b7b8ad;
        border-radius: 6px;
        padding: 0 10px;
        background: #fff;
        color: #1f2520;
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
        <label>Alias <input name="alias" required pattern="[A-Za-z0-9][A-Za-z0-9_.-]*"></label>
        <label>IP / Host <input name="ip" required></label>
        <label>Port <input name="port" type="number" min="1" max="65535" value="22"></label>
        <label>User <input name="user" value="root" required></label>
        <label>Auth
          <select name="method">
            <option value="">Inventory only</option>
            <option value="ssh">SSH key</option>
            <option value="password">Password</option>
          </select>
        </label>
        <label>Secret <input name="secret" type="password" autocomplete="off"></label>
        <button type="submit">Add VPS</button>
      </form>
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
      const form = document.querySelector("#create-form");

      document.querySelector("#refresh").addEventListener("click", loadHosts);
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const data = Object.fromEntries(new FormData(form));
        const body = {
          alias: data.alias,
          ip: data.ip,
          port: Number(data.port || 22),
          user: data.user
        };
        if (data.method === "ssh") {
          body.auth = { method: "ssh", private_key: data.secret };
        } else if (data.method === "password") {
          body.auth = { method: "password", password: data.secret };
        }
        await request("/vps", { method: "POST", body });
        form.reset();
        form.port.value = 22;
        form.user.value = "root";
        await loadHosts();
      });

      async function loadHosts() {
        const data = await request("/vps");
        hostsEl.innerHTML = "";
        for (const host of data.hosts || []) {
          const row = document.createElement("tr");
          row.innerHTML = [
            "<td>" + escapeHtml(host.alias) + "</td>",
            "<td>" + escapeHtml(host.ip) + "</td>",
            "<td>" + host.port + "</td>",
            "<td>" + escapeHtml(host.user) + "</td>",
            "<td class=\\"actions\\">" +
              "<button class=\\"secondary\\" data-audit=\\"" + escapeHtml(host.alias) + "\\" type=\\"button\\">Audit</button>" +
              "<button class=\\"secondary\\" data-delete=\\"" + escapeHtml(host.alias) + "\\" type=\\"button\\">Remove</button>" +
            "</td>"
          ].join("");
          hostsEl.append(row);
        }
      }

      hostsEl.addEventListener("click", async (event) => {
        const auditAlias = event.target.dataset.audit;
        const deleteAlias = event.target.dataset.delete;
        if (auditAlias) {
          await request("/vps/" + encodeURIComponent(auditAlias) + "/audit", { method: "POST" });
        }
        if (deleteAlias) {
          await request("/vps/" + encodeURIComponent(deleteAlias), { method: "DELETE" });
          await loadHosts();
        }
      });

      async function request(path, options = {}) {
        statusEl.textContent = "Working...";
        const init = { method: options.method || "GET" };
        if (options.body) {
          init.headers = { "Content-Type": "application/json" };
          init.body = JSON.stringify(options.body);
        }
        const response = await fetch(path, init);
        const data = await response.json();
        if (!response.ok) {
          statusEl.textContent = data.error || "Request failed";
          throw new Error(statusEl.textContent);
        }
        statusEl.textContent = "Ready";
        return data;
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

      loadHosts().catch((err) => {
        statusEl.textContent = err.message;
      });
    </script>
  </body>
</html>`;
