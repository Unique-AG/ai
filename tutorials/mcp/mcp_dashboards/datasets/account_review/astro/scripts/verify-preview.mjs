#!/usr/bin/env node
// Smoke test for the preview build: loads dist/preview/index.html in jsdom
// (so window.__MOCK_DATA__ / public/mock-host.js actually execute), then
// asserts the contract abstraction is doing its job — lists hydrate from
// mock data, and callTool/sendPrompt buttons behave like the real host.
import { readFileSync } from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const ROOT = path.resolve(import.meta.dirname, "..");
const htmlPath = path.join(ROOT, "dist/preview/index.html");
const mockHostSrc = readFileSync(path.join(ROOT, "public/mock-host.js"), "utf-8");

function assert(cond, message) {
  if (!cond) throw new Error(`FAIL: ${message}`);
  console.log(`  ok — ${message}`);
}

function getPath(row, path) {
  return String(path)
    .split(".")
    .reduce((value, key) => (value == null ? undefined : value[key]), row);
}

// runScripts: "dangerously" executes the page's two inline <script> tags
// (the __MOCK_DATA__ JSON.parse + the tag that would fetch /mock-host.js);
// resources are intentionally left at jsdom's default (no network), so the
// <script src="/mock-host.js"> fetch harmlessly no-ops and we eval the same
// file's source directly below instead.
const dom = new JSDOM(readFileSync(htmlPath, "utf-8"), {
  url: "http://localhost/",
  runScripts: "dangerously",
});
const { window } = dom;

window.eval(mockHostSrc);
window.document.dispatchEvent(new window.Event("DOMContentLoaded", { bubbles: true, cancelable: true }));

console.log("Attention rail + KPIs hydrate from mock data:");
const cards = window.document.querySelectorAll('[data-unique-list="attentionLive"] .acard');
const clients = JSON.parse(readFileSync(path.join(ROOT, "src/data/mock.json"), "utf-8")).clients;
const expectedAttentionCount = clients.filter((c) => {
  const status = getPath(c, "case_action.status");
  return status !== "Compliant" && status !== "Escalated";
}).length;
assert(
  cards.length === expectedAttentionCount,
  `${cards.length} attention cards rendered (expected ${expectedAttentionCount} open non-Escalated clients)`
);

const kpis = window.document.querySelectorAll('[data-unique-list="portfolioKpis"] .kpi');
assert(kpis.length === 4, `${kpis.length} portfolio KPI tiles rendered`);

const firstCard = cards[0];
assert(
  !!firstCard.querySelector('[data-unique-field="identity.name"]').textContent,
  "first card has a real identity.name (not a literal placeholder)"
);
const firstStatusTooltip = firstCard.querySelector(".status-indicator").getAttribute("data-tooltip");
const firstRiskTooltip = firstCard.querySelector(".risk-indicator").getAttribute("data-tooltip");
assert(firstStatusTooltip && !firstStatusTooltip.includes("{case_action.status}"), "status indicator tooltip is hydrated");
assert(firstRiskTooltip && !firstRiskTooltip.includes("{compliance.risk_level}"), "risk indicator tooltip is hydrated");

const unresolvedHref = window.document.querySelector('[href="client_href"]');
assert(!unresolvedHref, "client links resolve client_href (no literal placeholder hrefs)");

console.log("\nportfolio risk column is read-only:");
const firstAttentionHref = firstCard.getAttribute("href");
const matchingPortfolioLink = window.document.querySelector(`[data-unique-list="clientsLive"] a[href="${firstAttentionHref}"]`);
assert(!!matchingPortfolioLink, "first attention client also appears in the portfolio table");
const matchingPortfolioRow = matchingPortfolioLink.closest("tr");
const riskCell = matchingPortfolioRow.querySelector("td.riskcell .risk .cellval");
assert(!!riskCell?.textContent, "portfolio risk cell shows a risk level");
const riskEditBtn = matchingPortfolioRow.querySelector('button[data-unique-source-tool="update_client"]');
assert(!riskEditBtn, "portfolio risk cell has no inline update_client controls");

console.log("\nsendPrompt shows a fully-interpolated prompt (regression check for the earlier {placeholder} bug):");
const aiTrigger = window.document.querySelector(
  '[data-unique-list="clientPages"] label.banner-action[data-unique-action="sendPrompt"]',
);
assert(!!aiTrigger, "found at least one case action-bar sendPrompt trigger");
aiTrigger.click();
const toast = window.document.getElementById("mock-prompt-preview");
assert(!toast.hidden, "prompt preview toast is shown after clicking Analyse with AI");
assert(!toast.textContent.includes("{identity.name}"), "prompt text has no leftover {identity.name} placeholder");
assert(!toast.textContent.includes("{id}"), "prompt text has no leftover {id} placeholder");
const actDone = aiTrigger.closest(".act")?.querySelector(".act-done");
assert(actDone instanceof window.HTMLInputElement && actDone.checked, "action trigger hides after click (act-done checked)");
assert(window.getComputedStyle(aiTrigger).display === "none", "action trigger is not visible after click");

console.log("\nAll checks passed.");
