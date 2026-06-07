export class SemaphoreError extends Error {
  constructor(message, status, body) {
    super(message);
    this.name = "SemaphoreError";
    this.status = status;
    this.body = body;
  }
}

export class SemaphoreClient {
  constructor({ url, token, fetchImpl = fetch }) {
    if (!url) {
      throw new Error("SEMAPHORE_URL is required");
    }
    if (!token) {
      throw new Error("SEMAPHORE_API_TOKEN is required");
    }
    this.url = url.replace(/\/+$/, "");
    this.token = token;
    this.fetchImpl = fetchImpl.bind(globalThis);
  }

  getInventory(projectId, inventoryId) {
    return this.request(`/api/project/${projectId}/inventory/${inventoryId}`);
  }

  async updateInventory(projectId, inventory) {
    assertStaticInventory(inventory);
    await this.request(`/api/project/${projectId}/inventory/${inventory.id}`, {
      method: "PUT",
      body: inventoryUpdateBody(projectId, inventory),
      expectNoContent: true
    });
  }

  createKey(projectId, input) {
    const body = {
      name: input.name,
      project_id: Number(projectId),
      type: input.type
    };
    if (input.type === "ssh") {
      body.ssh = {
        login: input.login,
        private_key: input.privateKey,
        passphrase: input.passphrase || ""
      };
    } else if (input.type === "login_password") {
      body.login_password = {
        login: input.login,
        password: input.password
      };
    }
    return this.request(`/api/project/${projectId}/keys`, {
      method: "POST",
      body
    });
  }

  deleteKey(projectId, keyId) {
    return this.request(`/api/project/${projectId}/keys/${keyId}`, {
      method: "DELETE",
      expectNoContent: true
    });
  }

  triggerTask(projectId, templateId, vpsTask, options = {}) {
    const body = { template_id: Number(templateId) };
    if (options.limit) {
      body.limit = options.limit;
    }
    if (vpsTask) {
      body.environment = JSON.stringify({ vps_task: vpsTask });
    }
    return this.request(`/api/project/${projectId}/tasks`, {
      method: "POST",
      body
    });
  }

  async request(path, { method = "GET", body, expectNoContent = false } = {}) {
    const headers = {
      Authorization: `Bearer ${this.token}`
    };
    const init = { method, headers };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await this.fetchImpl(`${this.url}${path}`, init);
    const text = await response.text();
    if (!response.ok) {
      throw new SemaphoreError(extractError(text) || response.statusText, response.status, text);
    }
    if (expectNoContent || response.status === 204 || !text) {
      return null;
    }
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
}

function assertStaticInventory(inventory) {
  if (inventory?.type !== "static") {
    throw new Error(`Refusing to update non-static Semaphore inventory ${inventory?.id ?? "(unknown)"}`);
  }
}

function inventoryUpdateBody(projectId, inventory) {
  const body = {
    id: Number(inventory.id),
    name: inventory.name,
    project_id: Number(projectId),
    inventory: inventory.inventory,
    type: "static"
  };
  const hasSnakeKey = Object.hasOwn(inventory, "ssh_key_id");
  const hasCamelKey = Object.hasOwn(inventory, "sshKeyId");
  if (hasSnakeKey || hasCamelKey) {
    const sshKeyId = hasSnakeKey ? inventory.ssh_key_id : inventory.sshKeyId;
    body.ssh_key_id = sshKeyId === null ? null : Number(sshKeyId);
  }
  return body;
}

function extractError(text) {
  if (!text) {
    return "";
  }
  try {
    const parsed = JSON.parse(text);
    return parsed.error || parsed.message || text;
  } catch {
    return text;
  }
}
