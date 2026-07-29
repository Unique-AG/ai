// Unit tests for cases.ts's pure functions (rulePairs/renderCaseCss/
// renderOpenSectionsCss) and the caseDefinitionSchema validator, run
// against small hand-built fixtures rather than the real src/data/cases.json
// so a future edit to the real registry can't change what these assert.
import assert from "node:assert/strict";
import { test } from "node:test";
import { caseDefinitionSchema, renderCaseCss, renderOpenSectionsCss, rulePairs, type CaseDefinition } from "./cases.ts";

const docExpiry: CaseDefinition = {
  case_id: "doc-expiry",
  use_case: 1,
  rule_codes: ["R-DOC-EXPIRY"],
  tag: "Document / KYC refresh",
  icon: "📄",
  figure_title: "Documents & KYC",
  open_sections: ["docs-kyc"],
};

const advMedia: CaseDefinition = {
  case_id: "adverse-media",
  use_case: 2,
  rule_codes: ["R-SCR-ADVMEDIA", "R-SCR-PEP"],
  tag: 'Adverse-media "hit"',
  icon: "🔎",
  figure_title: "Screening match",
  figure2_title: "Secondary figure",
  figure_bars: true,
};

test("AI_rulePairs flattens multi-rule-code cases into one pair per rule code", () => {
  const pairs = rulePairs([docExpiry, advMedia]);
  assert.deepEqual(
    pairs.map(([ruleCode]) => ruleCode),
    ["R-DOC-EXPIRY", "R-SCR-ADVMEDIA", "R-SCR-PEP"]
  );
  assert.equal(pairs[1][1].case_id, "adverse-media");
});

test("AI_renderCaseCss emits visibility + escaped badge + figbar CSS per rule code", () => {
  const { visibility, badges, bars } = renderCaseCss([docExpiry, advMedia]);
  assert.match(visibility, /\[data-rule="R-DOC-EXPIRY"\]/);
  assert.match(visibility, /case-figure2\[data-rule="R-SCR-ADVMEDIA"\]/, "figure2_title cases get a case-figure2 visibility rule");
  assert.ok(!visibility.includes('case-figure2[data-rule="R-DOC-EXPIRY"'), "cases without figure2_title get no case-figure2 rule");
  assert.match(badges, /content: "Adverse-media \\"hit\\""/, "double quotes in a tag are escaped for the CSS content value");
  assert.match(bars, /R-SCR-ADVMEDIA.*figbar/s);
  assert.ok(!bars.includes("R-DOC-EXPIRY"), "cases without figure_bars get no bar rule");
});

test("AI_renderOpenSectionsCss force-opens only the sections a case names", () => {
  const css = renderOpenSectionsCss([docExpiry, advMedia]);
  assert.match(css, /\[data-rule="R-DOC-EXPIRY"\] \.sec\[data-key="docs-kyc"\]/);
  assert.ok(!css.includes("R-SCR-ADVMEDIA"), "a case with no open_sections contributes no rules");
});

test("AI_caseDefinitionSchema rejects a case with no rule_codes", () => {
  assert.throws(() => caseDefinitionSchema.parse({ ...docExpiry, rule_codes: [] }), /rule_codes/);
});

test("AI_caseDefinitionSchema rejects a dual_action with an empty actions list", () => {
  assert.throws(() => caseDefinitionSchema.parse({ ...docExpiry, dual_action: { actions: [] } }), /actions/);
});
