/**
 * mcp-live-host.js — like mock-host.js, but instead of reading
 * window.__MOCK_DATA__ it speaks real MCP (Streamable HTTP, JSON-RPC 2.0)
 * to a locally running, no-auth mcp_sqlite_excel server (see
 * `AUTH_DISABLED=true uv run mcp-sqlite-excel` in that package's README).
 * Used ONLY in the `live-local` build (see astro.config.mjs /
 * src/pages/index.astro) — a dev-only third mode for exercising the real
 * backend (list_rows/count_by/update_row/escalate_row/reset_from_excel)
 * from a browser with no platform host and no auth in between. Never
 * referenced by `live` (zero-JS platform artifact) or `preview` (local
 * mock data, no network).
 *
 * Why raw fetch() and not the `mcp` JS SDK: this stays a dependency-free
 * static file, same constraint as mock-host.js, and the whole point is to
 * exercise the exact wire protocol the platform's real connector speaks.
 *
 * Server URL: defaults to config.mcp_local_url (src/data/config.json),
 * overridable per-page-load with ?mcp=http://host:port/mcp — no rebuild
 * needed to point at a different local server.
 *
 * ---------------------------------------------------------------------
 * Streamable HTTP, the 20-second version (MCP spec 2025-03-26):
 *   1. POST {jsonrpc, id, method:"initialize", params:{protocolVersion,
 *      capabilities, clientInfo}} -> response carries a `mcp-session-id`
 *      response header; every later request must echo it back as a
 *      request header.
 *   2. POST {jsonrpc, method:"notifications/initialized"} (no `id` — a
 *      notification, not a request) -> 202 Accepted, empty body.
 *   3. POST {jsonrpc, id, method:"tools/call", params:{name, arguments}}
 *      for every actual tool call.
 * Every POST must send `Accept: application/json, text/event-stream` —
 * the server replies with either a single `application/json` body, or a
 * `text/event-stream` of one-or-more `event: message\ndata: {...}\n\n`
 * frames (this server always does the latter with AUTH_DISABLED=true,
 * confirmed against a real local instance). Either shape is handled below.
 *
 * The interesting wrinkle: `escalate_row`, `delete_row` and
 * `reset_from_excel` call `ctx.elicit(...)` server-side, which — mid the
 * *same* SSE stream opened for the tools/call — sends a JSON-RPC
 * *request* the other way (`elicitation/create`, with a JSON-Schema
 * `requestedSchema` describing a small form). The client must answer it
 * with a *separate* POST carrying a JSON-RPC *response* for that
 * request's id (still tagged with the same session), after which the
 * original stream resumes and eventually emits the tools/call result.
 * `renderElicitForm` below builds that form from `requestedSchema` on
 * the fly, so it works for any of these tools without hardcoding fields.
 */
(function () {
  "use strict";

  var FIELD_RE = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  var ATTR_PREFIX = "data-unique-attr-";
  var ROW_MARKER = "data-live-row";
  var PROTOCOL_VERSION = "2025-03-26";

  function resolveBaseUrl() {
    var fromQuery = new URLSearchParams(window.location.search).get("mcp");
    var fromConfig = window.__MCP_LIVE_CONFIG__ && window.__MCP_LIVE_CONFIG__.baseUrl;
    return fromQuery || fromConfig || "http://127.0.0.1:8004/mcp";
  }

  // ---- data-unique-* DOM interpreter (same contract as mock-host.js) ----

  function interpolate(template, row) {
    return template.replace(FIELD_RE, function (_, key) {
      return Object.prototype.hasOwnProperty.call(row, key) && row[key] != null ? String(row[key]) : "";
    });
  }

  function applyAttrBindings(root, row) {
    root.querySelectorAll("*").forEach(function (el) {
      for (var i = 0; i < el.attributes.length; i++) {
        var attr = el.attributes[i];
        if (attr.name.indexOf(ATTR_PREFIX) !== 0) continue;
        var targetAttr = attr.name.slice(ATTR_PREFIX.length);
        var raw = attr.value;
        var hasBraces = /\{[a-zA-Z_][a-zA-Z0-9_]*\}/.test(raw);
        var value = hasBraces
          ? interpolate(raw, row)
          : Object.prototype.hasOwnProperty.call(row, raw) && row[raw] != null
            ? String(row[raw])
            : raw;
        el.setAttribute(targetAttr, value);
      }
    });
  }

  function renderRow(templateEl, row) {
    var frag = templateEl.content.cloneNode(true);
    frag.querySelectorAll("[data-unique-field]").forEach(function (el) {
      var field = el.getAttribute("data-unique-field");
      el.textContent = row[field] != null ? row[field] : "";
    });
    applyAttrBindings(frag, row);
    return frag;
  }

  function setState(container, state) {
    container.querySelectorAll("[data-unique-state]").forEach(function (el) {
      el.style.display = el.getAttribute("data-unique-state") === state ? "" : "none";
    });
  }

  function showInlineError(container, message) {
    var el = container.querySelector('[data-unique-state="error"]') || container.querySelector('[data-unique-state="loading"]');
    if (!el) return;
    el.style.display = "";
    el.style.color = "#b42318";
    el.textContent = "⚠️ " + message;
  }

  /** Reads a dotted path (e.g. "rows") out of a tool result object. */
  function getPath(obj, path) {
    if (!path) return obj;
    return path.split(".").reduce(function (acc, key) {
      return acc == null ? undefined : acc[key];
    }, obj);
  }

  // ---------------------------- MCP client --------------------------------

  function McpClient(baseUrl) {
    this.baseUrl = baseUrl;
    this.sessionId = null;
    this.nextId = 1;
  }

  McpClient.prototype._post = function (body) {
    var headers = { "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
    if (this.sessionId) headers["mcp-session-id"] = this.sessionId;
    return fetch(this.baseUrl, { method: "POST", headers: headers, body: JSON.stringify(body) });
  };

  /** Feeds every JSON-RPC message in `response` to `onMessage`, in wire order. */
  McpClient.prototype._readMessages = async function (response, onMessage) {
    if (!this.sessionId) {
      var sid = response.headers.get("mcp-session-id");
      if (sid) this.sessionId = sid;
    }
    var contentType = response.headers.get("content-type") || "";
    if (contentType.indexOf("application/json") !== -1) {
      var text = await response.text();
      if (text) await onMessage(JSON.parse(text));
      return;
    }
    // text/event-stream: "event: message\r\ndata: {...}\r\n\r\n" frames (this
    // server emits CRLF line endings, per the SSE/HTTP convention — a plain
    // "\n\n" split misses every frame since "\r\n\r\n" contains no "\n\n"
    // substring), one JSON-RPC message per frame, arriving as the server
    // produces them.
    var reader = response.body.getReader();
    var decoder = new TextDecoder();
    var buffer = "";
    for (;;) {
      var chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      var frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop();
      for (var i = 0; i < frames.length; i++) {
        var dataLines = frames[i]
          .split(/\r?\n/)
          .filter(function (l) {
            return l.indexOf("data:") === 0;
          })
          .map(function (l) {
            return l.slice(5).trim();
          });
        if (!dataLines.length) continue;
        try {
          await onMessage(JSON.parse(dataLines.join("\n")));
        } catch (err) {
          console.error("[mcp-live-host] could not parse SSE frame", err, frames[i]);
        }
      }
    }
  };

  /**
   * Sends one JSON-RPC request and resolves with its `result`. Any
   * `elicitation/create` request arriving on the same stream first is
   * handed to `onElicit` (message.params) -> Promise<ElicitResult>; the
   * answer is POSTed back (a fresh request, same session) before reading
   * resumes.
   */
  McpClient.prototype.request = function (method, params, onElicit) {
    var self = this;
    var id = this.nextId++;
    return this._post({ jsonrpc: "2.0", id: id, method: method, params: params || {} }).then(function (response) {
      return new Promise(function (resolve, reject) {
        self
          ._readMessages(response, async function (msg) {
            if (msg.method === "elicitation/create") {
              var elicitResult = onElicit
                ? await onElicit(msg.params)
                : { action: "cancel" };
              await self._post({ jsonrpc: "2.0", id: msg.id, result: elicitResult });
              return;
            }
            if (msg.id === undefined || String(msg.id) !== String(id)) return; // unrelated notification
            if (msg.error) reject(new Error(msg.error.message || "MCP error"));
            else resolve(msg.result);
          })
          .catch(reject);
      });
    });
  };

  McpClient.prototype.notify = function (method, params) {
    return this._post({ jsonrpc: "2.0", method: method, params: params || {} });
  };

  McpClient.prototype.initialize = async function () {
    await this.request("initialize", {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { elicitation: {} },
      clientInfo: { name: "mcp-live-host", version: "0.1.0" },
    });
    await this.notify("notifications/initialized", {});
  };

  /**
   * Calls a tool and returns its parsed JSON payload. Every tool in this
   * server returns either a Pydantic model or a JSON string, but in both
   * cases `result.content[0].text` carries the same JSON text — simplest
   * to just always parse that, rather than special-case `structuredContent`
   * (which, for str-returning tools, wraps the *same string* under a
   * `{result: "..."}` shell rather than the parsed object).
   */
  McpClient.prototype.callTool = async function (name, args, onElicit) {
    var result = await this.request("tools/call", { name: name, arguments: args || {} }, onElicit);
    var text = result && result.content && result.content[0] && result.content[0].text;
    var parsed = text;
    try {
      parsed = JSON.parse(text);
    } catch (err) {
      // Not JSON — return the raw text.
    }
    if (result.isError) {
      var message = (parsed && parsed.message) || (typeof parsed === "string" ? parsed : "Tool call failed");
      throw new Error(name + ": " + message);
    }
    return parsed;
  };

  // ------------------------- elicitation form UI ---------------------------

  /**
   * Renders requestedSchema (a flat JSON Schema — string/bool/number
   * properties only, per the MCP elicitation spec) as a small modal form,
   * pre-filled from each property's `default`. Resolves to an ElicitResult.
   */
  function renderElicitForm(params) {
    return new Promise(function (resolve) {
      var schema = params.requestedSchema || { properties: {} };
      var props = schema.properties || {};

      var overlay = document.createElement("div");
      overlay.className = "mcp-elicit-overlay";
      var modal = document.createElement("form");
      modal.className = "mcp-elicit-modal";

      var heading = document.createElement("p");
      heading.className = "mcp-elicit-message";
      heading.textContent = params.message || "Confirm this action";
      modal.appendChild(heading);

      var inputs = {};
      Object.keys(props).forEach(function (key) {
        var def = props[key];
        var label = document.createElement("label");
        label.className = "mcp-elicit-field";
        var span = document.createElement("span");
        span.textContent = def.title || key;
        label.appendChild(span);

        var input;
        if (def.type === "boolean") {
          input = document.createElement("input");
          input.type = "checkbox";
          input.checked = def.default !== undefined ? !!def.default : false;
        } else if (def.description && def.description.length > 80) {
          input = document.createElement("textarea");
          input.rows = 3;
          input.value = def.default != null ? String(def.default) : "";
        } else {
          input = document.createElement("input");
          input.type = def.format === "email" || key.indexOf("email") !== -1 ? "email" : "text";
          input.value = def.default != null ? String(def.default) : "";
        }
        input.name = key;
        label.appendChild(input);
        if (def.description) {
          var hint = document.createElement("small");
          hint.textContent = def.description;
          label.appendChild(hint);
        }
        modal.appendChild(label);
        inputs[key] = input;
      });

      var actions = document.createElement("div");
      actions.className = "mcp-elicit-actions";

      function finish(result) {
        overlay.remove();
        resolve(result);
      }

      var cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "btn btn-ghost";
      cancelBtn.textContent = "Cancel";
      cancelBtn.addEventListener("click", function () {
        finish({ action: "cancel" });
      });

      var acceptBtn = document.createElement("button");
      acceptBtn.type = "submit";
      acceptBtn.className = "btn btn-ok";
      acceptBtn.textContent = "Confirm";

      actions.appendChild(cancelBtn);
      actions.appendChild(acceptBtn);
      modal.appendChild(actions);

      modal.addEventListener("submit", function (event) {
        event.preventDefault();
        var content = {};
        Object.keys(inputs).forEach(function (key) {
          var input = inputs[key];
          content[key] = input.type === "checkbox" ? input.checked : input.value;
        });
        finish({ action: "accept", content: content });
      });

      overlay.appendChild(modal);
      document.body.appendChild(overlay);
      var firstInput = modal.querySelector("input, textarea");
      if (firstInput) firstInput.focus();
    });
  }

  function injectElicitStyles() {
    var style = document.createElement("style");
    style.textContent =
      ".mcp-elicit-overlay{position:fixed;inset:0;background:rgba(10,14,25,.55);display:flex;align-items:center;justify-content:center;z-index:300}" +
      ".mcp-elicit-modal{background:#fff;border-radius:12px;padding:20px 22px;max-width:420px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,.35);display:flex;flex-direction:column;gap:12px;font:14px/1.5 system-ui,sans-serif}" +
      ".mcp-elicit-message{white-space:pre-wrap;margin:0 0 4px;color:#101827}" +
      ".mcp-elicit-field{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#374151}" +
      ".mcp-elicit-field input[type=text],.mcp-elicit-field input[type=email],.mcp-elicit-field textarea{font:inherit;padding:7px 9px;border:1px solid #d0d5dd;border-radius:8px}" +
      ".mcp-elicit-field small{color:#6b7280;font-size:11px}" +
      ".mcp-elicit-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:4px}";
    document.head.appendChild(style);
  }

  // ------------------------------- wiring -----------------------------------

  function hydrateList(client, container) {
    var tool = container.getAttribute("data-unique-source-tool");
    var argsRaw = container.getAttribute("data-unique-source-args");
    var path = container.getAttribute("data-unique-source-path");
    var args;
    try {
      args = argsRaw ? JSON.parse(argsRaw) : {};
    } catch (err) {
      console.error("[mcp-live-host] could not parse data-unique-source-args", err, argsRaw);
      args = {};
    }
    return client
      .callTool(tool, args)
      .then(function (result) {
        var rows = getPath(result, path);
        if (!Array.isArray(rows)) rows = [];
        var template = container.querySelector("template[data-unique-item]");
        if (!template) return;
        container.querySelectorAll("[" + ROW_MARKER + "]").forEach(function (n) {
          n.remove();
        });
        rows.forEach(function (row) {
          var frag = renderRow(template, row);
          Array.prototype.forEach.call(frag.children, function (n) {
            n.setAttribute(ROW_MARKER, "");
          });
          container.appendChild(frag);
        });
        setState(container, rows.length ? "ok" : "empty");
      })
      .catch(function (err) {
        console.error("[mcp-live-host] list hydrate failed", tool, args, err);
        showInlineError(container, err.message);
      });
  }

  function hydrateAll(client) {
    document.querySelectorAll("[data-unique-list]").forEach(function (container) {
      hydrateList(client, container);
    });
  }

  function showPromptToast(prompt) {
    var el = document.getElementById("mock-prompt-preview");
    if (!el) return;
    el.textContent = prompt;
    el.hidden = false;
    clearTimeout(el._hideTimer);
    el._hideTimer = setTimeout(function () {
      el.hidden = true;
    }, 12000);
  }

  function onClick(client, event) {
    var btn = event.target.closest("[data-unique-action]");
    if (!btn) return;
    var action = btn.getAttribute("data-unique-action");

    if (action === "sendPrompt") {
      var payloadRaw = btn.getAttribute("data-unique-payload");
      try {
        var payload = payloadRaw ? JSON.parse(payloadRaw) : {};
        showPromptToast(payload.prompt || "(empty prompt)");
      } catch (err) {
        console.error("[mcp-live-host] could not parse sendPrompt payload", err, payloadRaw);
      }
      return;
    }

    if (action === "callTool") {
      var tool = btn.getAttribute("data-unique-source-tool");
      var argsRaw = btn.getAttribute("data-unique-source-args");
      var refresh = (btn.getAttribute("data-unique-source-refresh") || "")
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
      var args;
      try {
        args = argsRaw ? JSON.parse(argsRaw) : {};
      } catch (err) {
        console.error("[mcp-live-host] could not parse callTool args", err, argsRaw);
        return;
      }
      btn.disabled = true;
      client
        .callTool(tool, args, renderElicitForm)
        .then(function () {
          refresh.forEach(function (listId) {
            var container = document.querySelector('[data-unique-list="' + listId + '"]');
            if (container) hydrateList(client, container);
          });
        })
        .catch(function (err) {
          console.error("[mcp-live-host] callTool failed", tool, args, err);
          window.alert("MCP call failed — " + tool + ": " + err.message);
        })
        .finally(function () {
          btn.disabled = false;
        });
    }
  }

  async function init() {
    injectElicitStyles();
    var baseUrl = resolveBaseUrl();
    var client = new McpClient(baseUrl);
    console.info("[mcp-live-host] connecting to", baseUrl, "(no MCP connector — real HTTP, AUTH_DISABLED assumed)");
    try {
      await client.initialize();
    } catch (err) {
      console.error("[mcp-live-host] initialize failed — is the server running with AUTH_DISABLED=true?", err);
      document.querySelectorAll('[data-unique-state="loading"]').forEach(function (el) {
        el.style.display = "";
        el.style.color = "#b42318";
        el.textContent = "⚠️ Could not reach MCP server at " + baseUrl + " — " + err.message;
      });
      return;
    }
    hydrateAll(client);
    document.addEventListener("click", function (event) {
      onClick(client, event);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
