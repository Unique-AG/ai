import { config } from "./config.ts";
import type { ClientRow, KpiRow } from "./schema.ts";

export const mcpServer = config.mcp_server;
export const pollMs = config.poll_ms;

/** Nested domain models use dotted field paths, so templates are validated by runtime schema parsing. */
type ValidTemplate<Row, S extends string> = S & (Row extends never ? never : unknown);

/**
 * Binds `.field(...)`/`.key(...)`/`.attr(...)`/`.attrTemplate(...)` to a
 * specific row shape, so call sites get autocomplete on `name` + a compile
 * error on a typo'd field name (e.g. `clientRow.field("clint_name")`)
 * instead of a silently-empty `data-unique-*` binding at render time — the
 * same guarantee a hand-written `interface` + a same-shaped `dict[str, Any]`
 * on the Python side can't give you, since `keyof Row` here comes straight
 * from `lib/schema.ts`'s zod schema and can never drift from it. `clientRow`/
 * `kpiRow` below are the two shapes this dashboard actually binds against.
 */
function createFieldHelpers<Row>() {
  /** `data-unique-field="<name>"` — e.g. `clientRow.field("open_issue")`. */
  function field(name: string) {
    return { "data-unique-field": name };
  }

  /** `data-unique-key="<name>"` — marks the row-identity field, e.g. `clientRow.key("row_id")`. */
  function key(name: string) {
    return { "data-unique-key": name };
  }

  /** `data-unique-attr-<attr>="<name>"` — bare form, no `{...}` interpolation, e.g. `clientRow.attr("data-status", "status")`. */
  function attr(attrName: string, name: string) {
    return { [`data-unique-attr-${attrName}`]: name };
  }

  /** `data-unique-attr-<attr>="<template>"` — every `{field}` inside `template` is checked against `Row`. */
  function attrTemplate<S extends string>(attrName: string, template: ValidTemplate<Row, S>) {
    return { [`data-unique-attr-${attrName}`]: template } as Record<string, S>;
  }

  return { field, key, attr, attrTemplate };
}

export const clientRow = createFieldHelpers<ClientRow>();
export const kpiRow = createFieldHelpers<KpiRow>();

export function dataListAttrs(opts: {
  listName: string;
  tool: string;
  args: Record<string, unknown>;
  path?: string;
}) {
  return {
    "data-unique-list": opts.listName,
    "data-unique-source-server": mcpServer,
    "data-unique-source-tool": opts.tool,
    "data-unique-source-args": JSON.stringify(opts.args),
    "data-unique-source-path": opts.path ?? "rows",
    "data-unique-source-poll": pollMs,
  };
}

// `argsTemplate` is deliberately plain `string`, not `ValidTemplate<ClientRow, S>`
// like `attrTemplate`/`sendPromptAttrs` below: its value is a *JSON* blob
// (e.g. `{"table":"clients","row_id":{row_id},...}`) whose own structural
// `{`/`}` characters would collide with FieldRefs' brace-matching, which
// only makes sense for plain text with isolated `{field}` placeholders
// (hrefs, tooltips, prose). Typo-checking that JSON's *keys* is instead the
// job of typing the function that builds it (see EditableCell.astro's
// `sourceArgs`, which takes `field: keyof ClientRow`).
type CallToolArgs = { args: Record<string, unknown> } | { argsTemplate: string };

export function callToolAttrs(opts: { tool: string; refresh: string } & CallToolArgs) {
  const source =
    "argsTemplate" in opts
      ? { "data-unique-attr-data-unique-source-args": opts.argsTemplate }
      : { "data-unique-source-args": JSON.stringify(opts.args) };

  return {
    "data-unique-action": "callTool",
    "data-unique-source-server": mcpServer,
    "data-unique-source-tool": opts.tool,
    ...source,
    "data-unique-source-refresh": opts.refresh,
  };
}

/**
 * `prompt` is checked the same way `attrTemplate` checks its template: every
 * `{field}` placeholder inside the prose must be a real `ClientRow` key.
 * Safe here (unlike `argsTemplate` above) because a prompt is plain text —
 * no structural JSON braces to collide with the placeholder ones.
 */
export function sendPromptAttrs<S extends string>(prompt: ValidTemplate<ClientRow, S>) {
  return {
    "data-unique-action": "sendPrompt",
    "data-unique-attr-data-unique-payload": JSON.stringify({ prompt }),
  };
}
