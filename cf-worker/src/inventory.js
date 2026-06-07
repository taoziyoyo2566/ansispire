const TARGET_GROUP = "vps_targets";
const TARGET_VARS_GROUP = "vps_targets:vars";

export function parseInventory(text = "") {
  const lines = String(text).split(/\r?\n/);
  const hosts = [];
  const groupVars = {};
  let section = "";

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line.startsWith(";")) {
      continue;
    }
    const sectionMatch = line.match(/^\[(.+)]$/);
    if (sectionMatch) {
      section = sectionMatch[1];
      continue;
    }
    if (section === TARGET_GROUP) {
      const host = parseHostLine(line);
      if (host) {
        hosts.push(host);
      }
      continue;
    }
    if (section === TARGET_VARS_GROUP) {
      const idx = line.indexOf("=");
      if (idx > 0) {
        groupVars[line.slice(0, idx)] = line.slice(idx + 1);
      }
    }
  }

  return { hosts, groupVars };
}

export function serializeInventory({ hosts = [], groupVars = defaultGroupVars() } = {}) {
  const out = [`[${TARGET_GROUP}]`];
  for (const host of hosts) {
    out.push(formatHostLine(host));
  }
  out.push("");
  out.push(`[${TARGET_VARS_GROUP}]`);
  for (const [key, value] of Object.entries(groupVars)) {
    out.push(`${key}=${value}`);
  }
  return `${out.join("\n")}\n`;
}

export function listHosts(inventoryText) {
  return parseInventory(inventoryText).hosts.map(hostToResponse);
}

export function upsertHost(inventoryText, hostInput) {
  const parsed = parseInventory(inventoryText);
  const host = normalizeHost(hostInput);
  const idx = parsed.hosts.findIndex((item) => item.alias === host.alias);
  if (idx >= 0) {
    parsed.hosts[idx] = { ...parsed.hosts[idx], ...host };
  } else {
    parsed.hosts.push(host);
  }
  return serializeInventory(parsed);
}

export function removeHost(inventoryText, alias) {
  const parsed = parseInventory(inventoryText);
  const nextHosts = parsed.hosts.filter((host) => host.alias !== alias);
  if (nextHosts.length === parsed.hosts.length) {
    throw new Error("alias not found");
  }
  return serializeInventory({ ...parsed, hosts: nextHosts });
}

export function findHost(inventoryText, alias) {
  return parseInventory(inventoryText).hosts.find((host) => host.alias === alias) || null;
}

export function defaultGroupVars() {
  return {
    ansible_python_interpreter: "/usr/bin/python3",
    ansible_ssh_common_args: "-o StrictHostKeyChecking=accept-new"
  };
}

export function normalizeAlias(alias) {
  const value = String(alias || "").trim();
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(value)) {
    throw new Error("alias must start with a letter or digit and contain only letters, digits, dot, dash, or underscore");
  }
  return value;
}

export function normalizeHost(input) {
  const alias = normalizeAlias(input.alias);
  const ip = requiredString(input.ip, "ip");
  const port = normalizePort(input.port ?? 22);
  const user = requiredString(input.user || input.ansible_user || "ansible", "user");
  const host = {
    alias,
    ip,
    port,
    user
  };
  if (input.vars && typeof input.vars === "object") {
    host.vars = { ...input.vars };
  }
  if (input.keyId !== undefined && input.keyId !== null) {
    host.keyId = Number(input.keyId);
  }
  return host;
}

function parseHostLine(line) {
  const parts = splitFields(line);
  if (parts.length === 0) {
    return null;
  }
  const vars = {};
  for (const part of parts.slice(1)) {
    const idx = part.indexOf("=");
    if (idx > 0) {
      vars[part.slice(0, idx)] = unquoteValue(part.slice(idx + 1));
    }
  }
  const host = {
    alias: parts[0],
    vars,
    ip: vars.ansible_host || parts[0],
    port: Number(vars.ansible_port || 22),
    user: vars.ansible_user || "ansible"
  };
  if (vars.ansible_ssh_private_key_id !== undefined) {
    host.keyId = Number(vars.ansible_ssh_private_key_id);
  }
  return host;
}

function formatHostLine(host) {
  const vars = {
    ...(host.vars || {}),
    ansible_host: host.ip,
    ansible_port: String(host.port),
    ansible_user: host.user
  };
  if (host.keyId !== undefined && Number.isFinite(Number(host.keyId))) {
    vars.ansible_ssh_private_key_id = String(host.keyId);
  }
  return `${host.alias} ${Object.entries(vars).map(([key, value]) => `${key}=${quoteIfNeeded(value)}`).join(" ")}`;
}

function hostToResponse(host) {
  return {
    alias: host.alias,
    ip: host.ip,
    port: host.port,
    user: host.user,
    ...(host.keyId !== undefined ? { keyId: host.keyId } : {})
  };
}

function splitFields(line) {
  const fields = [];
  let current = "";
  let quote = "";
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if ((char === "'" || char === '"') && !quote) {
      quote = char;
      current += char;
      continue;
    }
    if (char === quote) {
      quote = "";
      current += char;
      continue;
    }
    if (/\s/.test(char) && !quote) {
      if (current) {
        fields.push(current);
        current = "";
      }
      continue;
    }
    current += char;
  }
  if (current) {
    fields.push(current);
  }
  return fields;
}

function quoteIfNeeded(value) {
  const raw = String(value);
  if (/[\s"'=]/.test(raw)) {
    return JSON.stringify(raw);
  }
  return raw;
}

function unquoteValue(value) {
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    try {
      return JSON.parse(value);
    } catch {
      return value.slice(1, -1);
    }
  }
  return value;
}

function normalizePort(port) {
  const value = Number(port);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error("port must be an integer from 1 to 65535");
  }
  return value;
}

function requiredString(value, name) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    throw new Error(`${name} is required`);
  }
  return normalized;
}
