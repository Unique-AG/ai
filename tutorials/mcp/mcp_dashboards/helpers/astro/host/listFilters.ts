/**
 * Client-side list filter helpers for portfolio search / dropdown bars.
 *
 * Filter controls declare `data-unique-filter-bar="<listId>"` on a wrapper and
 * individual inputs inside it. Hosts merge the live values into a list's base
 * tool args before hydrating.
 */
import { type Row, readPath } from "./dom.ts";

/** Reads filter/search values targeting a `[data-unique-list]` id. */
export function readListFilterArgs(listId: string): Row {
  const bar = document.querySelector(`[data-unique-filter-bar="${listId}"]`);
  if (!bar) return {};

  const merged: Row = {};
  const searchEl = bar.querySelector<HTMLInputElement>("[data-unique-filter-search]");
  const search = searchEl?.value.trim();
  if (search) merged.search = search;

  const filters: Row = {};
  bar.querySelectorAll<HTMLElement>("[data-unique-filter-field]").forEach((el) => {
    const field = el.getAttribute("data-unique-filter-field");
    if (!field) return;
    const value = el instanceof HTMLSelectElement ? el.value : (el as HTMLInputElement).value.trim();
    if (value) filters[field] = value;
  });
  if (Object.keys(filters).length) merged.filters = filters;

  const dueEl = bar.querySelector<HTMLSelectElement>("[data-unique-filter-due]");
  const due = dueEl?.value.trim();
  if (due) merged.due_filter = due;

  return merged;
}

/** Merges a list's static tool args with any live filter-bar values. */
export function mergeListArgs(base: Row, listId: string): Row {
  const live = readListFilterArgs(listId);
  const baseFilters = (typeof base.filters === "object" && base.filters !== null ? base.filters : {}) as Row;
  const liveFilters = (typeof live.filters === "object" && live.filters !== null ? live.filters : {}) as Row;
  const merged: Row = { ...base, ...live };
  if (Object.keys(baseFilters).length || Object.keys(liveFilters).length) {
    merged.filters = { ...baseFilters, ...liveFilters };
  }
  if (!live.search) delete merged.search;
  if (!live.due_filter) delete merged.due_filter;
  return merged;
}

/** Wires filter controls to re-hydrate their target list on change. */
export function bindListFilters(onChange: (listId: string) => void): void {
  const wired = new Set<Element>();
  for (const bar of document.querySelectorAll("[data-unique-filter-bar]")) {
    if (wired.has(bar)) continue;
    wired.add(bar);
    const listId = bar.getAttribute("data-unique-filter-bar");
    if (!listId) continue;
    bar.addEventListener("input", () => onChange(listId));
    bar.addEventListener("change", () => onChange(listId));
  }
}

const ISO_DATE_RE = /^(\d{4}-\d{2}-\d{2})$/;

function parseIsoDate(value: unknown): string | null {
  if (value == null || value === "") return null;
  const text = String(value).trim();
  const match = ISO_DATE_RE.exec(text);
  return match ? match[1]! : null;
}

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function dueDateBucket(value: unknown): "none" | "urgent" | "scheduled" {
  const iso = parseIsoDate(value);
  if (!iso) return "none";
  return iso <= todayIso() ? "urgent" : "scheduled";
}

/** Applies the portfolio due-date dropdown client-side (not a server filter yet). */
export function applyDueDateFilter(rows: Row[], dueFilter: unknown): Row[] {
  const due = typeof dueFilter === "string" ? dueFilter : "";
  if (!due) return rows;
  return rows.filter((row) => dueDateBucket(readPath(row, "case_action.due_date")) === due);
}

/** Computes portfolio header KPI rows from a client array. */
export function portfolioKpiRows(rows: Row[]): Row[] {
  const needs = (row: Row) => readPath(row, "case_action.status") === "Needs Remediation";
  const actNow = rows.filter((row) => needs(row) && readPath(row, "compliance.criticality") === "RED").length;
  const breach = rows.filter((row) => needs(row) && readPath(row, "case_action.rule_code") === "R-SUIT-ALLOC").length;
  const watch = rows.filter((row) => needs(row) && readPath(row, "compliance.criticality") === "AMBER").length;
  return [
    { bucket: "total", label: "Total Clients", count: rows.length },
    { bucket: "act_now", label: "Act now", count: actNow },
    { bucket: "breach", label: "Breach", count: breach },
    { bucket: "watch", label: "Watch", count: watch },
  ];
}
