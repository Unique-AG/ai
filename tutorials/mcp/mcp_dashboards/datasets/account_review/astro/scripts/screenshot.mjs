#!/usr/bin/env node
/**
 * Visual smoke check for the preview build.
 *
 * Why this exists
 * ----------------
 * `npm run verify` only asserts on the DOM (counts, attributes, interpolated
 * text) — it can't catch pure-CSS layout bugs, like a wrapper element
 * accidentally landing inside an ancestor that gets `display: none` (the
 * `.client-pages` vs `.view-main` nesting bug this script caught). This
 * renders the actual preview build in headless Chromium and writes PNGs so
 * you can eyeball the console and a client detail page.
 *
 * Usage
 * -----
 *   npm run build:preview   # must run first — this reads dist/preview
 *   npm run screenshot
 *
 * Writes ./screenshots/console.png and ./screenshots/client.png.
 */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PREVIEW_DIR = path.join(ROOT, "..", "dist", "preview");
const OUT_DIR = path.join(ROOT, "..", "screenshots");
const PORT = 8935;

const CONTENT_TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };

await mkdir(OUT_DIR, { recursive: true });

const server = createServer(async (req, res) => {
  const reqPath = req.url === "/" ? "/index.html" : req.url;
  try {
    const filePath = path.join(PREVIEW_DIR, decodeURIComponent(reqPath));
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
  await page.goto(`http://localhost:${PORT}/`, { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(OUT_DIR, "console.png"), fullPage: true });

  await page.click("a.c-nm");
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(OUT_DIR, "client.png"), fullPage: true });

  console.log(`Wrote ${path.relative(process.cwd(), OUT_DIR)}/console.png and client.png`);
} finally {
  await browser.close();
  server.close();
}
