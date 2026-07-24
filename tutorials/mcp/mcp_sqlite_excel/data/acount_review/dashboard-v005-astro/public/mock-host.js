/**
 * mock-host.js — a tiny, local stand-in for the Unique platform's
 * data-unique-* binding engine, used ONLY in the `preview` build
 * (see astro.config.mjs / src/pages/index.astro). It is never referenced by
 * the `live` build, which stays byte-for-byte the same zero-JS contract that
 * ships to the platform.
 *
 * Why this is safe to write once, generically: every data-unique-* page in
 * this codebase already follows one small, consistent contract —
 *
 *   <div data-unique-list="ID" data-unique-source-tool="..." data-unique-source-args="...">
 *     <template data-unique-item> ... data-unique-field / data-unique-attr-* ... </template>
 *     <p data-unique-state="loading|empty|error"> ... </p>
 *   </div>
 *
 *   <button data-unique-action="callTool|sendPrompt" data-unique-source-tool="..."
 *           data-unique-attr-data-unique-source-args='{"row_id":{row_id},...}'>
 *
 * — so one interpreter can hydrate *any* page built this way from a plain
 * JSON fixture (window.__MOCK_DATA__, keyed by list id) instead of a live
 * MCP connector. Nothing here is specific to this dashboard's markup.
 *
 * `data-unique-attr-*` semantics (mirrors the real platform host):
 *   - value has no "{...}"   -> whole value is a field NAME, copy row[value]
 *   - value contains "{...}" -> template string, replace each {field} in
 *                                place (used for hrefs, CSS widths, and JSON
 *                                args/payloads where {row_id} sits next to
 *                                literal JSON braces)
 *
 * window.__MOCK_DATA__ is keyed by TABLE name (e.g. "clients"), not by list
 * id — every data-unique-list here queries the same "clients" table with
 * different filters/limit (list_rows) or grouping (count_by), so each list
 * re-derives its rows from that one canonical array at hydrate time (see
 * queryTable below, a minimal client-side mirror of
 * mcp_sqlite_excel's repository.list_rows/count_by). That keeps every list
 * consistent after a mutation without modelling per-list joins here.
 */
(function () {
  "use strict";

  var FIELD_RE = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  var ATTR_PREFIX = "data-unique-attr-";

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

  /** Minimal client-side mirror of repository.list_rows/count_by. */
  function queryTable(mockData, tool, args) {
    var table = (args && args.table) || "clients";
    var rows = mockData[table] || [];
    if (tool === "count_by") {
      var column = (args && args.column) || "status";
      var counts = {};
      var order = [];
      rows.forEach(function (row) {
        var key = row[column] == null ? "(null)" : String(row[column]);
        if (!(key in counts)) order.push(key);
        counts[key] = (counts[key] || 0) + 1;
      });
      return order.map(function (bucket) {
        return { bucket: bucket, label: bucket, count: counts[bucket] };
      });
    }
    // list_rows (default)
    var filters = (args && args.filters) || {};
    var filtered = rows.filter(function (row) {
      return Object.keys(filters).every(function (key) {
        return String(row[key]) === String(filters[key]);
      });
    });
    return args && args.limit ? filtered.slice(0, args.limit) : filtered;
  }

  function hydrateList(container, mockData) {
    var tool = container.getAttribute("data-unique-source-tool");
    var argsRaw = container.getAttribute("data-unique-source-args");
    var args;
    try {
      args = argsRaw ? JSON.parse(argsRaw) : {};
    } catch (err) {
      console.error("[mock-host] could not parse data-unique-source-args", err, argsRaw);
      args = {};
    }
    var rows = queryTable(mockData, tool, args);
    var template = container.querySelector("template[data-unique-item]");
    if (!template) return;

    container.querySelectorAll("[data-mock-row]").forEach(function (n) {
      n.remove();
    });
    rows.forEach(function (row) {
      var frag = renderRow(template, row);
      Array.prototype.forEach.call(frag.children, function (n) {
        n.setAttribute("data-mock-row", "");
      });
      container.appendChild(frag);
    });
    setState(container, rows.length ? "ok" : "empty");
  }

  function hydrateAll(mockData) {
    document.querySelectorAll("[data-unique-list]").forEach(function (container) {
      hydrateList(container, mockData);
    });
  }

  function applyToolEffect(mockData, tool, args) {
    if (!args) return;
    if (tool === "update_row" || tool === "escalate_row") {
      var patch = Object.assign({}, args.fields);
      if (tool === "escalate_row" && !args.fields) patch.status = "Escalated";
      var table = mockData[args.table] || [];
      table.forEach(function (row) {
        if (String(row.row_id) === String(args.row_id)) Object.assign(row, patch);
      });
    } else if (tool === "reset_from_excel") {
      console.info("[mock-host] reset_from_excel is a no-op in preview mode — reload the page to reset.");
    } else {
      console.info("[mock-host] unhandled tool in preview mode:", tool, args);
    }
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

  function onClick(mockData, event) {
    var btn = event.target.closest("[data-unique-action]");
    if (!btn) return;
    var action = btn.getAttribute("data-unique-action");
    var tool = btn.getAttribute("data-unique-source-tool");

    if (action === "sendPrompt") {
      var payloadRaw = btn.getAttribute("data-unique-payload");
      try {
        var payload = payloadRaw ? JSON.parse(payloadRaw) : {};
        showPromptToast(payload.prompt || "(empty prompt)");
      } catch (err) {
        console.error("[mock-host] could not parse sendPrompt payload", err, payloadRaw);
      }
      return;
    }

    if (action === "callTool") {
      var argsRaw = btn.getAttribute("data-unique-source-args");
      var refresh = (btn.getAttribute("data-unique-source-refresh") || "")
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
      try {
        var args = argsRaw ? JSON.parse(argsRaw) : {};
        applyToolEffect(mockData, tool, args);
        refresh.forEach(function (listId) {
          var container = document.querySelector('[data-unique-list="' + listId + '"]');
          if (container) hydrateList(container, mockData);
        });
      } catch (err) {
        console.error("[mock-host] could not parse callTool args", err, argsRaw);
      }
    }
  }

  function init() {
    var mockData = window.__MOCK_DATA__ || {};
    hydrateAll(mockData);
    document.addEventListener("click", function (event) {
      onClick(mockData, event);
    });
    console.info(
      "[mock-host] preview mode — hydrated",
      Object.keys(mockData)
        .map(function (k) {
          return k + ":" + mockData[k].length;
        })
        .join(", "),
      "(no MCP connector, all data is local)"
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
