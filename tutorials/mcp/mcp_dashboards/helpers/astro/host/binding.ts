/**
 * Row shaping for local dashboard hosts (preview + live-local).
 *
 * Mirrors `helpers/python/src/mcp_dashboards/binding.py` so the same
 * `data-unique-attr-href="client_href"` bindings resolve whether rows come
 * from mock JSON or a FastMCP server that already enriched them.
 */
import type { Row } from "./dom.ts";

/** Recursively mirror nested dict/list values as top-level dotted keys. */
export function flattenDottedPaths(value: unknown, prefix = ""): Row {
  const out: Row = {};
  if (value == null || typeof value !== "object" || Array.isArray(value)) return out;

  for (const [key, child] of Object.entries(value as Row)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child != null && typeof child === "object" && !Array.isArray(child)) {
      Object.assign(out, flattenDottedPaths(child, path));
    } else if (Array.isArray(child)) {
      child.forEach((item, index) => {
        const itemPath = `${path}.${index}`;
        if (item != null && typeof item === "object" && !Array.isArray(item)) {
          Object.assign(out, flattenDottedPaths(item, itemPath));
        } else {
          out[itemPath] = item;
        }
      });
    } else {
      out[path] = child;
    }
  }
  return out;
}

/** Return a row with nested data, dotted mirrors, and platform attr helpers. */
export function enrichBindingRow(row: Row): Row {
  const flat = flattenDottedPaths(row);
  const merged: Row = { ...row, ...flat };

  const clientId = row.id;
  if (clientId != null) {
    merged.client_href = `#client-${clientId}`;
    merged.client_dom_id = `client-${clientId}`;
  }

  const riskLevel = flat["compliance.risk_level"];
  if (riskLevel != null) {
    merged["compliance.risk_level_tooltip"] = `${riskLevel} risk`;
  }

  for (const [key, value] of Object.entries(flat)) {
    if (key.endsWith(".pct") && value != null) {
      merged[`${key}_bar_style`] = `width:${value}%`;
    }
  }

  return merged;
}
