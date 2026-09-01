/**
 * The `data-unique-*` DOM interpreter, shared by both local hosts.
 *
 * This is the single implementation of the contract documented in
 * `docs/dom-contract.md`. `preview` (mockHost) and `live-local` (liveHost)
 * differ only in where rows come from; everything about reading bindings out of
 * the DOM and writing rows back into it lives here.
 *
 * Bundled into `public/` by `scripts/build-hosts.mjs`. The `live` build ships no
 * host at all — the platform provides its own.
 */

import { enrichBindingRow } from "./binding.ts";

export type Row = Record<string, unknown>;
export type ListState = "loading" | "ok" | "empty" | "error";

const FIELD_RE = /\{([a-zA-Z_][a-zA-Z0-9_.]*)\}/g;
const HAS_FIELD_RE = /\{[a-zA-Z_][a-zA-Z0-9_.]*\}/;
const ATTR_PREFIX = "data-unique-attr-";
const ROW_MARKER = "data-unique-row";
const ROW_KEY_MARKER = "data-unique-row-key";
const PROMPT_TOAST_ID = "mock-prompt-preview";
const PROMPT_TOAST_MS = 12_000;

/** Reads a dotted path out of a row or tool result. Returns undefined at any missing link. */
export function readPath(source: unknown, path: string | null | undefined): unknown {
  if (!path) return source;
  // Prefer exact top-level keys (platform helpers like `compliance.risk_level_tooltip`).
  if (source != null && typeof source === "object" && !Array.isArray(source)) {
    const row = source as Row;
    if (Object.prototype.hasOwnProperty.call(row, path)) return row[path];
  }
  return String(path)
    .split(".")
    .reduce<unknown>((value, key) => {
      if (value == null || typeof value !== "object") return undefined;
      return (value as Row)[key];
    }, source);
}

/** Writes a dotted path into a row, creating intermediate objects as needed. */
export function writePath(target: Row, path: string, value: unknown): void {
  const keys = String(path).split(".");
  let cursor: Row = target;
  for (const key of keys.slice(0, -1)) {
    if (cursor[key] == null || typeof cursor[key] !== "object") cursor[key] = {};
    cursor = cursor[key] as Row;
  }
  cursor[keys[keys.length - 1]!] = value;
}

/** Replaces every `{dotted.path}` in a template string with the row's value. */
export function interpolate(template: string, row: Row): string {
  return template.replace(FIELD_RE, (_match, key: string) => {
    const value = readPath(row, key);
    return value != null ? String(value) : "";
  });
}

/**
 * Resolves `data-unique-attr-X="..."` into a real `X` attribute.
 *
 * A value containing `{...}` is treated as a template; a bare value is treated
 * as a single field name. This two-phase indirection is what lets a `<template>`
 * carry per-row `href`s and JSON tool arguments without the browser acting on
 * the un-interpolated version.
 */
export function applyAttrBindings(root: ParentNode, row: Row): void {
  // `querySelectorAll` never returns the root itself, but a row's own root
  // element carries bindings too (the client page's `id`, for one), so it has to
  // be included explicitly when rebinding an already-rendered row in place.
  const scope = root instanceof Element ? [root, ...root.querySelectorAll<HTMLElement>("*")] : [...root.querySelectorAll<HTMLElement>("*")];
  scope.forEach((el) => {
    for (const attr of Array.from(el.attributes)) {
      if (!attr.name.startsWith(ATTR_PREFIX)) continue;
      const target = attr.name.slice(ATTR_PREFIX.length);
      const raw = attr.value;
      if (HAS_FIELD_RE.test(raw)) {
        el.setAttribute(target, interpolate(raw, row));
        continue;
      }
      const value = readPath(row, raw);
      el.setAttribute(target, value != null ? String(value) : raw);
    }
  });
}

/** Writes every `data-unique-field` inside (and on) `root` from the row. */
function applyFieldBindings(root: ParentNode, row: Row): void {
  const scope =
    root instanceof Element
      ? [root, ...root.querySelectorAll<HTMLElement>("[data-unique-field]")]
      : [...root.querySelectorAll<HTMLElement>("[data-unique-field]")];
  for (const el of scope) {
    const path = el.getAttribute("data-unique-field");
    if (path === null) continue;
    const value = readPath(row, path);
    el.textContent = value != null ? String(value) : "";
  }
}

/**
 * Binds a row into a subtree.
 *
 * Safe to run repeatedly on the same element: the `data-unique-field` and
 * `data-unique-attr-*` source attributes are read, never consumed, so rebinding
 * simply overwrites the previously written text and attributes.
 */
function bindRow(root: ParentNode, row: Row): void {
  const enriched = enrichBindingRow(row);
  applyFieldBindings(root, enriched);
  applyAttrBindings(root, enriched);
}

/** Clones a row template and fills every field and attribute binding in it. */
export function renderRow(template: HTMLTemplateElement, row: Row): DocumentFragment {
  const frag = template.content.cloneNode(true) as DocumentFragment;
  bindRow(frag, row);
  return frag;
}

/** Shows the one `[data-unique-state]` placeholder matching `state`, hides the rest. */
export function setListState(container: Element, state: ListState): void {
  container.querySelectorAll<HTMLElement>("[data-unique-state]").forEach((el) => {
    el.style.display = el.getAttribute("data-unique-state") === state ? "" : "none";
  });
}

/** Surfaces a failure in the list's own error placeholder rather than only the console. */
export function showListError(container: Element, message: string): void {
  setListState(container, "error");
  const el =
    container.querySelector<HTMLElement>('[data-unique-state="error"]') ??
    container.querySelector<HTMLElement>('[data-unique-state="loading"]');
  if (!el) return;
  el.style.display = "";
  el.textContent = `⚠️ ${message}`;
}

export interface ListBindings {
  tool: string;
  args: Row;
  path: string | null;
}

/** Reads the source bindings off a `[data-unique-list]` container. */
export function readListBindings(container: Element, log: Logger): ListBindings {
  return {
    tool: container.getAttribute("data-unique-source-tool") ?? "",
    args: parseJsonAttr(container.getAttribute("data-unique-source-args"), "data-unique-source-args", log),
    path: container.getAttribute("data-unique-source-path"),
  };
}

/**
 * Reconciles the container's rendered rows against `rows`, keyed by the
 * template's `data-unique-key` field.
 *
 * A row that is still present keeps its existing element and is rebound in
 * place; only genuinely new rows are created and only departed rows are removed.
 * Nothing is moved unless the order actually changed.
 *
 * This matters beyond avoiding flicker. The client detail page is routed by CSS
 * `:target` (`.view-client:target`), so it is displayed only while the browser's
 * target element is the `<main id="client-N">` that a row rendered. Destroying
 * and recreating that element — which a plain re-render does on every poll and
 * after every mutation — leaves `:target` matching nothing and silently returns
 * the reader to the main view. Preserving element identity is what keeps an open
 * client page open, along with its scroll position and focus.
 *
 * A template with no `data-unique-key` cannot be reconciled, so it falls back to
 * replacing every row.
 */
export function renderRows(container: Element, rows: Row[]): void {
  const template = container.querySelector<HTMLTemplateElement>("template[data-unique-item]");
  if (!template) return;

  const keyPath = template.content.querySelector("[data-unique-key]")?.getAttribute("data-unique-key") ?? null;
  const previous = Array.from(container.querySelectorAll(`:scope > [${ROW_MARKER}]`));
  const reusable = new Map<string, Element>();
  if (keyPath !== null) {
    for (const el of previous) {
      const key = el.getAttribute(ROW_KEY_MARKER);
      if (key !== null && !reusable.has(key)) reusable.set(key, el);
    }
  }

  const ordered: Element[] = [];
  const kept = new Set<Element>();
  for (const row of rows) {
    const rowKey = keyPath !== null ? readPath(row, keyPath) : undefined;
    const key = rowKey != null ? String(rowKey) : null;
    const existing = key !== null ? reusable.get(key) : undefined;

    if (existing && !kept.has(existing)) {
      bindRow(existing, row);
      ordered.push(existing);
      kept.add(existing);
      continue;
    }

    const frag = renderRow(template, row);
    if (frag.childElementCount > 1) {
      console.error(
        `[data-unique] template in list "${container.getAttribute("data-unique-list")}" has ` +
          `${frag.childElementCount} root elements; a row template must have exactly one, ` +
          "since the row's identity is the element's identity. Extra roots are ignored.",
      );
    }
    const created = frag.firstElementChild;
    if (!created) continue;
    created.setAttribute(ROW_MARKER, "");
    if (key !== null) created.setAttribute(ROW_KEY_MARKER, key);
    ordered.push(created);
    kept.add(created);
  }

  for (const el of previous) {
    if (!kept.has(el)) el.remove();
  }

  // Position each row after the previous one, touching the DOM only where the
  // order is actually wrong — so the steady state moves nothing at all.
  let prior: Element | null = null;
  for (const el of ordered) {
    if (prior === null) {
      const firstRow = container.querySelector(`:scope > [${ROW_MARKER}]`);
      if (firstRow !== el) {
        if (firstRow) firstRow.before(el);
        else container.appendChild(el);
      }
    } else if (prior.nextElementSibling !== el) {
      prior.after(el);
    }
    prior = el;
  }

  setListState(container, rows.length ? "ok" : "empty");
}

export function listContainers(): Element[] {
  return Array.from(document.querySelectorAll("[data-unique-list]"));
}

export function listContainerById(listId: string): Element | null {
  return document.querySelector(`[data-unique-list="${listId}"]`);
}

export type Logger = (message: string, ...rest: unknown[]) => void;

export function parseJsonAttr(raw: string | null, attrName: string, log: Logger): Row {
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Row;
  } catch (err) {
    log(`could not parse ${attrName}`, err, raw);
    return {};
  }
}

/** Dev-only stand-in for the platform's prompt handoff. */
export function showPromptToast(prompt: string): void {
  const el = document.getElementById(PROMPT_TOAST_ID);
  if (!el) return;
  el.textContent = prompt;
  el.hidden = false;
  const timers = window as unknown as { __promptToastTimer?: ReturnType<typeof setTimeout> };
  clearTimeout(timers.__promptToastTimer);
  timers.__promptToastTimer = setTimeout(() => {
    el.hidden = true;
  }, PROMPT_TOAST_MS);
}

export interface ToolAction {
  tool: string;
  args: Row;
  /** List ids to re-hydrate once the call succeeds. */
  refresh: string[];
  button: HTMLButtonElement;
}

/**
 * Delegates clicks on `[data-unique-action]`.
 *
 * `sendPrompt` behaves the same in both hosts, so it is handled here;
 * `callTool` is host-specific and dispatched to `onCallTool`.
 */
export function bindActions(onCallTool: (action: ToolAction) => void | Promise<void>, log: Logger): void {
  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const trigger = target.closest<HTMLElement>("[data-unique-action]");
    if (!trigger) return;
    const action = trigger.getAttribute("data-unique-action");

    if (action === "sendPrompt") {
      const payload = parseJsonAttr(trigger.getAttribute("data-unique-payload"), "data-unique-payload", log);
      showPromptToast(typeof payload.prompt === "string" ? payload.prompt : "(empty prompt)");
      return;
    }

    if (action !== "callTool") return;
    void onCallTool({
      tool: trigger.getAttribute("data-unique-source-tool") ?? "",
      args: parseJsonAttr(trigger.getAttribute("data-unique-source-args"), "data-unique-source-args", log),
      refresh: (trigger.getAttribute("data-unique-source-refresh") ?? "")
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      button: trigger as HTMLButtonElement,
    });
  });
}

/**
 * Re-hydrates each container on its own `data-unique-source-poll` interval
 * (emitted from `config.poll_ms` by `dataListAttrs`).
 *
 * Only the live-local host calls this: preview data can only change through a
 * click, which already refreshes the lists it declares.
 */
export function startPolling(hydrate: (container: Element) => void, log: Logger): void {
  for (const container of listContainers()) {
    const pollMs = Number(container.getAttribute("data-unique-source-poll") ?? "");
    if (!Number.isFinite(pollMs) || pollMs <= 0) continue;
    log(`polling ${container.getAttribute("data-unique-list")} every ${pollMs}ms`);
    setInterval(() => {
      if (document.visibilityState === "hidden") return;
      hydrate(container);
    }, pollMs);
  }
}

export function onReady(start: () => void): void {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
}

export function prefixedLogger(prefix: string): { log: Logger; error: Logger } {
  return {
    log: (message, ...rest) => console.info(`[${prefix}] ${message}`, ...rest),
    error: (message, ...rest) => console.error(`[${prefix}] ${message}`, ...rest),
  };
}
