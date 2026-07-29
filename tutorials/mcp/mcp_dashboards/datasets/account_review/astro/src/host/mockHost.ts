/**
 * `preview` host — hydrates the page from `window.__MOCK_DATA__` instead of a
 * live MCP server, with no network access at all.
 *
 * Unlike the live host, this one is necessarily dataset-specific: it is a
 * client-side mirror of the account_review server's list / count / update
 * semantics. The DOM work is all done by the shared interpreter; only the query
 * behaviour below is local.
 *
 * The fixture is keyed by table name (`clients`), not by list id: every
 * `data-unique-list` on the page queries the same clients array with different
 * filters or grouping, so each list re-derives its rows from that one canonical
 * typed array at hydrate time. A mutation therefore stays consistent across
 * every list bound to the same table, like the real backend.
 *
 * `mock.json` is validated against the generated Zod schema at build time by
 * `src/lib/mode.ts`, so there is no second runtime check here.
 */
import {
  applyDueDateFilter,
  bindListFilters,
  mergeListArgs,
  portfolioKpiRows,
} from "@mcp-dashboards/host/listFilters.ts";
import {
  type Row,
  bindActions,
  listContainerById,
  listContainers,
  onReady,
  prefixedLogger,
  readListBindings,
  readPath,
  renderRows,
  writePath,
} from "@mcp-dashboards/host/dom.ts";

import { domainPath } from "../lib/domainFields.ts";

type MockData = Record<string, Row[]>;

const { log, error } = prefixedLogger("mock-host");

function matchesSearch(row: Row, search: string): boolean {
  const needle = search.toLowerCase();
  const name = String(readPath(row, domainPath("identity.name")) ?? "").toLowerCase();
  const reference = String(readPath(row, domainPath("identity.reference")) ?? "").toLowerCase();
  return name.includes(needle) || reference.includes(needle);
}

/** Client-side mirror of the dataset's list and count tools. */
function queryTable(mock: MockData, tool: string, args: Row): Row[] {
  const rows = mock[typeof args.table === "string" ? args.table : "clients"] ?? [];

  if (tool === "portfolio_kpis") {
    return portfolioKpiRows(rows);
  }

  if (tool === "count_clients_by" || tool === "count_by") {
    const column = domainPath(typeof args.column === "string" ? args.column : "case_action.status");
    const counts = new Map<string, number>();
    for (const row of rows) {
      const value = readPath(row, column);
      const key = value == null ? "(null)" : String(value);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return Array.from(counts, ([bucket, count]) => ({ bucket, label: bucket, count }));
  }

  const filters = (typeof args.filters === "object" && args.filters !== null ? args.filters : {}) as Row;
  let matched = rows.filter((row) =>
    Object.entries(filters).every(([key, value]) => String(readPath(row, domainPath(key))) === String(value)),
  );

  const search = typeof args.search === "string" ? args.search.trim() : "";
  if (search) matched = matched.filter((row) => matchesSearch(row, search));

  matched = applyDueDateFilter(matched, args.due_filter);

  return typeof args.limit === "number" ? matched.slice(0, args.limit) : matched;
}

function hydrate(mock: MockData, container: Element): void {
  const { tool, args } = readListBindings(container, error);
  const listId = container.getAttribute("data-unique-list") ?? "";
  const effectiveArgs = listId ? mergeListArgs(args, listId) : args;
  renderRows(container, queryTable(mock, tool, effectiveArgs));
}

function hydrateAll(mock: MockData, listId?: string): void {
  for (const container of listContainers()) {
    const id = container.getAttribute("data-unique-list") ?? "";
    if (listId && id !== listId) continue;
    hydrate(mock, container);
  }
}

/** Applies a tool's effect to the in-memory fixture, since there is no server. */
function applyToolEffect(mock: MockData, tool: string, args: Row): void {
  if (tool !== "update_client") {
    log(`${tool} is not simulated in preview mode — reload the page to reset`);
    return;
  }
  const patch = (typeof args.fields === "object" && args.fields !== null ? args.fields : {}) as Row;
  const table = mock[typeof args.table === "string" ? args.table : "clients"] ?? [];
  const pk = String(args.pk ?? args.id);
  for (const row of table) {
    if (String(row.id) !== pk) continue;
    for (const [key, value] of Object.entries(patch)) {
      writePath(row, domainPath(key), value);
    }
  }
}

function start(): void {
  const mock = ((window as unknown as { __MOCK_DATA__?: MockData }).__MOCK_DATA__ ?? {}) as MockData;

  hydrateAll(mock);
  bindListFilters((listId) => hydrateAll(mock, listId));

  bindActions(({ tool, args, refresh }) => {
    applyToolEffect(mock, tool, args);
    for (const listId of refresh) {
      const container = listContainerById(listId);
      if (container) hydrate(mock, container);
    }
    const kpiContainer = listContainerById("portfolioKpis");
    if (kpiContainer) hydrate(mock, kpiContainer);
  }, error);

  const summary = Object.entries(mock)
    .map(([table, rows]) => `${table}:${rows.length}`)
    .join(", ");
  log(`preview mode — hydrated ${summary} (no MCP connector, all data is local)`);
}

onReady(start);
