/**
 * `live-local` host — the same DOM contract as the preview host, but backed by a
 * real MCP server over Streamable HTTP.
 *
 * Dataset-agnostic: a dataset supplies its own tool-response schemas and calls
 * `startLiveHost`. Everything here is driven by the `data-unique-*` attributes on
 * the page, so it never needs to know a tool's name or shape.
 *
 * This is a dev-only mode for exercising a real backend from a browser with no
 * platform host and no auth in between. The `live` build ships no host at all,
 * and `preview` never touches the network.
 */
import {
  type Row,
  type ToolAction,
  bindActions,
  listContainerById,
  listContainers,
  onReady,
  prefixedLogger,
  readListBindings,
  readPath,
  renderRows,
  showListError,
  startPolling,
} from "./dom.ts";
import { applyDueDateFilter, bindListFilters, mergeListArgs } from "./listFilters.ts";
import { injectElicitStyles, renderElicitForm } from "./elicitForm.ts";
import { McpClient } from "./mcpClient.ts";

const { log, error } = prefixedLogger("mcp-live-host");

/**
 * A generated Zod schema, described structurally.
 *
 * Deliberately not `import type { ZodTypeAny } from "zod"`: keeping the shared
 * host free of any zod import means it has no npm dependencies at all, and it
 * sidesteps the `instanceof` hazard that appears when a dataset app and this
 * package resolve two different copies of zod.
 */
export interface ToolResultSchema {
  parse(payload: unknown): unknown;
}

export interface LiveHostOptions {
  /**
   * Response schema per tool name, generated from the dataset's
   * `contract/main.tsp`. A tool with no entry is not validated.
   */
  toolResultSchemas?: Record<string, ToolResultSchema>;
}

interface SchemaIssue {
  path: (string | number)[];
  message: string;
}

/** Structural check for a Zod validation error, for the reason given above. */
function schemaIssuesOf(err: unknown): SchemaIssue[] | null {
  const issues = (err as { issues?: unknown })?.issues;
  return Array.isArray(issues) ? (issues as SchemaIssue[]) : null;
}

function resolveBaseUrl(): string {
  const fromQuery = new URLSearchParams(window.location.search).get("mcp");
  const fromConfig = (window as unknown as { __MCP_LIVE_CONFIG__?: { baseUrl?: string } }).__MCP_LIVE_CONFIG__
    ?.baseUrl;
  const baseUrl = fromQuery ?? fromConfig;
  if (!baseUrl) {
    // No hardcoded default: a silent fallback made a misconfigured build look
    // like a working one. config.json's mcp_local_url is the single source.
    throw new Error("No MCP URL — set mcp_local_url in src/data/config.json or pass ?mcp=http://host:port/mcp");
  }
  return baseUrl;
}

/**
 * Validates a tool payload against its generated schema.
 *
 * Unknown tools pass through untouched; a known tool whose payload does not
 * match the contract raises, because rendering half-valid data is how a drift
 * stays hidden.
 */
function validateToolResult(schemas: Record<string, ToolResultSchema>, tool: string, payload: unknown): unknown {
  const schema = schemas[tool];
  if (!schema) return payload;
  try {
    return schema.parse(payload);
  } catch (err) {
    const issues = schemaIssuesOf(err);
    if (!issues) throw err;
    error(`${tool} returned a payload that does not match the generated contract`, issues);
    const summary = issues
      .slice(0, 3)
      .map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`)
      .join("; ");
    throw new Error(`${tool} response failed contract validation — ${summary}`);
  }
}

function makeCallTool(client: McpClient, schemas: Record<string, ToolResultSchema>) {
  return async function callTool(tool: string, args: Row, onElicit?: typeof renderElicitForm): Promise<unknown> {
    const payload = await client.callTool(tool, args, onElicit);
    return validateToolResult(schemas, tool, payload);
  };
}

type CallTool = ReturnType<typeof makeCallTool>;

async function hydrate(callTool: CallTool, container: Element): Promise<void> {
  const { tool, args, path } = readListBindings(container, error);
  const listId = container.getAttribute("data-unique-list") ?? "";
  const effectiveArgs = listId ? mergeListArgs(args, listId) : args;
  try {
    const result = await callTool(tool, effectiveArgs);
    let rows = readPath(result, path);
    if (!Array.isArray(rows)) rows = [];
    if (tool === "list_clients" && effectiveArgs.due_filter) {
      rows = applyDueDateFilter(rows as Row[], effectiveArgs.due_filter);
    }
    renderRows(container, rows as Row[]);
  } catch (err) {
    error("list hydrate failed", tool, effectiveArgs, err);
    showListError(container, err instanceof Error ? err.message : String(err));
  }
}

async function onCallTool(callTool: CallTool, { tool, args, refresh, button }: ToolAction): Promise<void> {
  button.disabled = true;
  try {
    await callTool(tool, args, renderElicitForm);
    await Promise.all(
      refresh.map((listId) => {
        const container = listContainerById(listId);
        return container ? hydrate(callTool, container) : Promise.resolve();
      }),
    );
  } catch (err) {
    error("callTool failed", tool, args, err);
    window.alert(`MCP call failed — ${tool}: ${err instanceof Error ? err.message : String(err)}`);
  } finally {
    button.disabled = false;
  }
}

function reportUnreachable(baseUrl: string, err: unknown): void {
  const message = err instanceof Error ? err.message : String(err);
  for (const container of listContainers()) {
    showListError(container, `Could not reach MCP server at ${baseUrl} — ${message}`);
  }
}

async function start(options: LiveHostOptions): Promise<void> {
  injectElicitStyles();

  let baseUrl: string;
  try {
    baseUrl = resolveBaseUrl();
  } catch (err) {
    error("no MCP URL configured", err);
    reportUnreachable("(unconfigured)", err);
    return;
  }

  const client = new McpClient(baseUrl);
  const callTool = makeCallTool(client, options.toolResultSchemas ?? {});
  log(`connecting to ${baseUrl} (no MCP connector — real HTTP, local no-auth server assumed)`);
  try {
    await client.initialize();
  } catch (err) {
    error(`initialize failed — is the server running at ${baseUrl}?`, err);
    reportUnreachable(baseUrl, err);
    return;
  }

  await Promise.all(listContainers().map((container) => hydrate(callTool, container)));
  bindListFilters((listId) => {
    const container = listContainerById(listId);
    if (container) void hydrate(callTool, container);
  });
  bindActions((action) => onCallTool(callTool, action), error);
  startPolling((container) => void hydrate(callTool, container), log);
}

/** Entry point for a dataset's `live-local` host bundle. */
export function startLiveHost(options: LiveHostOptions = {}): void {
  onReady(() => void start(options));
}
