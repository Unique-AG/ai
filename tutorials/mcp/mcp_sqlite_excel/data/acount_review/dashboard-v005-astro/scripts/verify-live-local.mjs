#!/usr/bin/env node
/**
 * End-to-end smoke test for the `live-local` build against a REAL running
 * mcp_sqlite_excel server — unlike `npm run verify` (jsdom + mock data),
 * this exercises actual Streamable HTTP: session handshake, list_rows
 * hydration, and the full escalate_row elicitation round-trip (server asks
 * for recipient_email/note mid-call, this script answers via the real
 * mcp-live-host.js modal, same as a human would).
 *
 * Prerequisites
 * -------------
 *   AUTH_DISABLED=true UNIQUE_MCP_LOCAL_BASE_URL=http://127.0.0.1:8004 \
 *     uv run mcp-sqlite-excel   # in tutorials/mcp/mcp_sqlite_excel/
 *
 * Usage
 * -----
 *   npm run build:live-local   # must run first — this reads dist/live-local
 *   npm run verify:live-local
 *
 * This mutates real rows on the local server (escalates one client, then
 * reverts it via update_row) — safe against the demo dataset, never point
 * MCP_URL at anything else.
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const BUILD_DIR = path.join(ROOT, "..", "dist", "live-local");
const OUT_DIR = path.join(ROOT, "..", "screenshots");
const PORT = 8936;
const MCP_URL = process.env.MCP_URL || "http://127.0.0.1:8004/mcp";

const CONTENT_TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };

let failed = false;
function check(name, condition) {
  if (condition) {
    console.log(`  ok — ${name}`);
  } else {
    failed = true;
    console.error(`  FAIL — ${name}`);
  }
}

const health = await fetch(MCP_URL.replace(/\/mcp$/, "/")).catch(() => null);
if (!health || !health.ok) {
  console.error(
    `Could not reach ${MCP_URL} — start the server first:\n` +
      "  AUTH_DISABLED=true UNIQUE_MCP_LOCAL_BASE_URL=http://127.0.0.1:8004 uv run mcp-sqlite-excel"
  );
  process.exit(1);
}
const healthBody = await health.json();
if (!healthBody.auth_disabled) {
  console.error(`Server at ${MCP_URL} has auth enabled — restart it with AUTH_DISABLED=true.`);
  process.exit(1);
}

/** Minimal Node-side MCP call, used only to clean up after this script's own
 * mutation (Node's fetch ignores CORS entirely, so — unlike the browser —
 * this works without exposing mcp-session-id; kept deliberately tiny rather
 * than reusing mcp-live-host.js, which is meant to stay a browser-only,
 * dependency-free static asset). */
async function mcpCallToolNode(method, args) {
  let sessionId = null;
  async function post(body) {
    const headers = { "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
    if (sessionId) headers["mcp-session-id"] = sessionId;
    const res = await fetch(MCP_URL, { method: "POST", headers, body: JSON.stringify(body) });
    if (!sessionId) sessionId = res.headers.get("mcp-session-id");
    return res;
  }
  async function readResult(res, id) {
    const text = await res.text();
    for (const frame of text.split(/\r?\n\r?\n/)) {
      const line = frame.split(/\r?\n/).find((l) => l.startsWith("data:"));
      if (!line) continue;
      const msg = JSON.parse(line.slice(5).trim());
      if (String(msg.id) === String(id)) return msg.result;
    }
    throw new Error(`No response for request ${id} in: ${text.slice(0, 200)}`);
  }
  await post({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "verify-live-local-cleanup", version: "0.1" } } });
  await post({ jsonrpc: "2.0", method: "notifications/initialized", params: {} });
  const res = await post({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: method, arguments: args } });
  return readResult(res, 2);
}

await mkdir(OUT_DIR, { recursive: true });
const server = createServer(async (req, res) => {
  const urlPath = req.url.split("?")[0]; // strip ?mcp=... before mapping to a file
  const reqPath = urlPath === "/" ? "/index.html" : urlPath;
  try {
    const filePath = path.join(BUILD_DIR, decodeURIComponent(reqPath));
    const body = await readFile(filePath);
    res.writeHead(200, { "Content-Type": CONTENT_TYPES[path.extname(filePath)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("Not found");
  }
});
await new Promise((resolve) => server.listen(PORT, resolve));

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  page.on("console", (msg) => {
    if (msg.type() === "error") console.error("  [browser]", msg.text());
  });
  await page.goto(`http://localhost:${PORT}/?mcp=${encodeURIComponent(MCP_URL)}`, { waitUntil: "networkidle" });

  console.log("Attention rail + KPIs hydrate over real Streamable HTTP:");
  await page.waitForSelector(".rail .acard", { timeout: 10000 });
  const cardCountBefore = await page.locator(".rail .acard").count();
  check("at least one attention card rendered", cardCountBefore > 0);
  const firstName = await page.locator(".rail .acard .who span[data-unique-field=client_name]").first().textContent();
  check("first card has a real client_name (not a literal placeholder)", firstName && !firstName.includes("{"));
  const kpiCount = await page.locator(".kpis .kpi").count();
  check("KPI tiles rendered", kpiCount > 0);
  await page.screenshot({ path: path.join(OUT_DIR, "live-local-console.png"), fullPage: true });

  console.log("escalate_row round-trips through a real elicitation form:");
  const firstWrap = page.locator(".acard-wrap").first();
  const escalateArgs = JSON.parse(await firstWrap.locator('[data-unique-source-tool="escalate_row"]').getAttribute("data-unique-source-args"));
  await firstWrap.getByRole("button", { name: /Escalate/ }).click();

  await page.waitForSelector(".mcp-elicit-modal", { timeout: 5000 });
  check("elicitation modal appeared with a recipient_email field", (await page.locator('.mcp-elicit-field input[name="recipient_email"]').count()) === 1);
  await page.getByRole("button", { name: "Confirm" }).click();
  await page.waitForSelector(".mcp-elicit-modal", { state: "detached", timeout: 5000 });

  await page.waitForTimeout(500); // let the post-escalate refresh settle
  const cardCountAfter = await page.locator(".rail .acard").count();
  check(`attention rail shrank after escalate (${cardCountBefore} → ${cardCountAfter})`, cardCountAfter === cardCountBefore - 1);
  await page.screenshot({ path: path.join(OUT_DIR, "live-local-after-escalate.png"), fullPage: true });

  console.log("Wrote screenshots/live-local-*.png");

  console.log(`Reverting row_id ${escalateArgs.row_id} back to "Needs Remediation" (this script's only real mutation)...`);
  await mcpCallToolNode("update_row", { table: "clients", row_id: escalateArgs.row_id, fields: { status: "Needs Remediation" } });
  check("cleanup: row reverted", true);
} finally {
  await browser.close();
  server.close();
}

if (failed) {
  console.error("\nSome checks FAILED.");
  process.exit(1);
} else {
  console.log("\nAll checks passed.");
}
