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
const expectedAttentionCount = clients.filter((c) => getPath(c, "case_action.status") === "Needs Remediation").length;
assert(
  cards.length === expectedAttentionCount,
  `${cards.length} attention cards rendered (expected ${expectedAttentionCount} "Needs Remediation" clients)`
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

console.log("\ncallTool (portfolio risk edit) mutates state and refreshes bound lists:");
const firstAttentionHref = firstCard.getAttribute("href");
const matchingPortfolioLink = window.document.querySelector(`[data-unique-list="clientsLive"] a[href="${firstAttentionHref}"]`);
assert(!!matchingPortfolioLink, "first attention client also appears in the portfolio table");
const matchingPortfolioRow = matchingPortfolioLink.closest("tr");
const riskCell = matchingPortfolioRow.querySelector(".risk .cellval");
const beforeRisk = riskCell.textContent;
const mediumRiskBtn = Array.from(matchingPortfolioRow.querySelectorAll('button[data-unique-source-tool="update_client"]')).find((button) =>
  button.getAttribute("data-unique-source-args").includes('"risk_level":"Medium"')
);
assert(!!mediumRiskBtn, "portfolio Medium risk button present for first attention client");
assert(!mediumRiskBtn.getAttribute("data-unique-source-args").includes("{id}"), "Medium risk button args are fully interpolated (no leftover {id})");
mediumRiskBtn.dispatchEvent(new window.Event("click", { bubbles: true }));
assert(riskCell.textContent === "Medium", `risk cell updated after inline edit (${beforeRisk} → ${riskCell.textContent})`);

console.log("\nsendPrompt shows a fully-interpolated prompt (regression check for the earlier {placeholder} bug):");
const aiButton = window.document.querySelector('[data-unique-list="clientPages"] button[data-unique-action="sendPrompt"]');
assert(!!aiButton, "found at least one case action-bar button");
aiButton.dispatchEvent(new window.Event("click", { bubbles: true }));
const toast = window.document.getElementById("mock-prompt-preview");
assert(!toast.hidden, "prompt preview toast is shown after clicking Analyse with AI");
assert(!toast.textContent.includes("{identity.name}"), "prompt text has no leftover {identity.name} placeholder");
assert(!toast.textContent.includes("{id}"), "prompt text has no leftover {id} placeholder");

console.log("\nAll checks passed.");
