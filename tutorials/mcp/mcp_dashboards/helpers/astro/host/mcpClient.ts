/**
 * Minimal MCP client over Streamable HTTP (JSON-RPC 2.0), used only by the
 * `live-local` dashboard to talk to a local no-auth FastMCP server.
 *
 * Deliberately raw `fetch` rather than the MCP JS SDK: the point of this mode is
 * to exercise the exact wire protocol the platform connector speaks.
 *
 * Handshake (MCP spec 2025-03-26):
 *   1. POST `initialize` → the response carries an `mcp-session-id` header that
 *      every later request must echo back.
 *   2. POST the `notifications/initialized` notification (no `id`).
 *   3. POST `tools/call` per tool invocation.
 *
 * Every POST sends `Accept: application/json, text/event-stream`; the server may
 * answer with a single JSON body or a stream of `event: message` frames. Both
 * are handled. If a tool elicits input, the server sends an
 * `elicitation/create` request on the same stream, which is answered with a
 * separate POST before reading resumes.
 */

const PROTOCOL_VERSION = "2025-03-26";

export interface ElicitRequest {
  message?: string;
  requestedSchema?: {
    properties?: Record<string, ElicitProperty>;
  };
}

export interface ElicitProperty {
  type?: string;
  title?: string;
  description?: string;
  format?: string;
  default?: unknown;
}

export type ElicitResult =
  | { action: "accept"; content: Record<string, string | boolean> }
  | { action: "cancel" }
  | { action: "decline" };

export type ElicitHandler = (request: ElicitRequest) => Promise<ElicitResult>;

interface JsonRpcMessage {
  id?: string | number;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: { message?: string };
}

interface ToolCallResult {
  isError?: boolean;
  content?: Array<{ text?: string }>;
}

export class McpClient {
  // Plain field + assignment rather than a constructor parameter property, so
  // these modules also load under `node --test`'s type stripping.
  readonly baseUrl: string;
  private sessionId: string | null = null;
  private nextId = 1;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private post(body: unknown): Promise<Response> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
    };
    if (this.sessionId) headers["mcp-session-id"] = this.sessionId;
    return fetch(this.baseUrl, { method: "POST", headers, body: JSON.stringify(body) });
  }

  /** Feeds every JSON-RPC message in `response` to `onMessage`, in wire order. */
  private async readMessages(
    response: Response,
    onMessage: (message: JsonRpcMessage) => Promise<void> | void,
  ): Promise<void> {
    if (!this.sessionId) {
      const sid = response.headers.get("mcp-session-id");
      if (sid) this.sessionId = sid;
    }
    if (!response.ok && response.status !== 202) {
      throw new Error(`HTTP ${response.status} ${response.statusText} from ${this.baseUrl}`);
    }

    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const text = await response.text();
      if (text) await onMessage(JSON.parse(text) as JsonRpcMessage);
      return;
    }
    if (!response.body) return;

    // SSE frames are separated by a blank line. This server emits CRLF, so a
    // plain "\n\n" split would never match.
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const data = frame
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim());
        if (data.length === 0) continue;
        try {
          await onMessage(JSON.parse(data.join("\n")) as JsonRpcMessage);
        } catch (err) {
          console.error("[mcp-live-host] could not parse SSE frame", err, frame);
        }
      }
    }
  }

  /** Sends one JSON-RPC request and resolves with its `result`. */
  private async request(method: string, params?: unknown, onElicit?: ElicitHandler): Promise<unknown> {
    const id = this.nextId++;
    const response = await this.post({ jsonrpc: "2.0", id, method, params: params ?? {} });
    return new Promise<unknown>((resolve, reject) => {
      this.readMessages(response, async (message) => {
        if (message.method === "elicitation/create") {
          const answer = onElicit
            ? await onElicit((message.params ?? {}) as ElicitRequest)
            : ({ action: "cancel" } as ElicitResult);
          await this.post({ jsonrpc: "2.0", id: message.id, result: answer });
          return;
        }
        if (message.id === undefined || String(message.id) !== String(id)) return;
        if (message.error) reject(new Error(message.error.message ?? "MCP error"));
        else resolve(message.result);
      }).catch(reject);
    });
  }

  async initialize(): Promise<void> {
    await this.request("initialize", {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { elicitation: {} },
      clientInfo: { name: "mcp-live-host", version: "0.1.0" },
    });
    await this.post({ jsonrpc: "2.0", method: "notifications/initialized", params: {} });
  }

  /**
   * Calls a tool and returns its parsed JSON payload.
   *
   * Both model-returning and string-returning tools put the same JSON text in
   * `content[0].text`, so that is always the thing to parse. A tool that failed
   * arrives with `isError` set and is raised here.
   */
  async callTool(name: string, args?: Record<string, unknown>, onElicit?: ElicitHandler): Promise<unknown> {
    const result = (await this.request("tools/call", { name, arguments: args ?? {} }, onElicit)) as ToolCallResult;
    const text = result?.content?.[0]?.text;
    let parsed: unknown = text;
    try {
      parsed = JSON.parse(text ?? "");
    } catch {
      // Not JSON — keep the raw text so the error message below stays useful.
    }
    if (result?.isError) {
      const message =
        (typeof parsed === "object" && parsed !== null && typeof (parsed as { message?: string }).message === "string"
          ? (parsed as { message: string }).message
          : typeof parsed === "string"
            ? parsed
            : null) ?? "Tool call failed";
      throw new Error(`${name}: ${message}`);
    }
    return parsed;
  }
}
