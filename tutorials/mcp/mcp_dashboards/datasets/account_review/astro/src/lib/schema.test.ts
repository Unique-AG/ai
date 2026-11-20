// Unit tests for the pure, DOM-free parts of schema.ts: the zod schemas
// parse a realistic nested Client and reject malformed values. No jsdom/Astro build
// needed — see ../../scripts/verify-preview.mjs for the end-to-end,
// rendered-HTML checks this complements.
import assert from "node:assert/strict";
import { test } from "node:test";
import { clientRowSchema, figureSchema, kpiRowSchema, readFigure, type ClientRow } from "./schema.ts";

const FIGURE_PREFIXES = ["fig", "perf", "mand", "hold"] as const;
const FIGURE_GROUP_BY_PREFIX = {
  fig: "documents",
  perf: "performance",
  mand: "mandate",
  hold: "holdings",
} as const;

/** One fully-populated, otherwise-arbitrary client row — every field `clientRowSchema` requires, nothing more. */
function makeClientRowFixture(): Record<string, unknown> {
  const row: Record<string, unknown> = {
    id: 1,
    identity: {
      name: "Ada Lovelace",
      reference: "CH-priv-0001",
      crd_number: "CRD-CH-0001",
      type: "Individual",
      segment: "Private Wealth",
    },
    contact: {
      date_of_birth: "1980-01-01",
      occupation: "Engineer",
      marital_status: "Single",
      nationality: "British",
      residence: "Switzerland",
      domicile: "Switzerland",
      incorporation: null,
      residential_address: "1 Main St, Geneva",
      email: "ada@example.ch",
      phone: "+41 79 000 0000",
    },
    portfolio: {
      onboarded: "2019-01-01",
      currency: "CHF",
      value: 1_000_000,
    },
    compliance: {
      risk_level: "Low",
      risk_profile: "Balanced",
      risk_tolerance: "Medium",
      criticality: "-",
      pep: "No",
      adverse_media: "No",
      sanctions: "No",
      fatca_us_person: "No",
      verification_source: "WorldCheck",
      documents_on_file: "passport",
      mandate_type: "Discretionary",
      client_categorization: "Professional",
      category_required: null,
      category_review_status: "Up to date",
    },
    review_schedule: {
      last_reviewed: "2026-01-01",
      next_review_due: "2027-01-01",
      kyc_refresh_due: "2027-01-01",
    },
    suitability: {
      investment_horizon: "Long-term",
      knowledge_experience: "Extensive",
      last_suitability_test: "2025-01-01",
      suitability_outcome: "Suitable",
    },
    case_action: {
      status: "Compliant",
      rule_code: "R-NONE",
      open_issue: "None",
      recommended_action: "None",
      due_date: "2026-06-01",
      title: "No action needed",
      explanation: "Everything is in order.",
      button_label: "Review",
      button_target: "#top",
      owner: "RM",
    },
    figures: {
      documents: [],
      performance: [],
      mandate: [],
      holdings: [],
    },
  };
  for (const prefix of FIGURE_PREFIXES) {
    const group = FIGURE_GROUP_BY_PREFIX[prefix];
    (row.figures as Record<string, unknown[]>)[group] = [1, 2, 3].map((slot) => ({
      label: `${prefix} label ${slot}`,
      value: `${prefix} value ${slot}`,
      pct: slot === 2 ? null : slot * 10,
      status: "ok",
    }));
  }
  return row;
}

test("AI_clientRowSchema parses a fully-populated nested client", () => {
  const fixture = makeClientRowFixture();
  const parsed = clientRowSchema.parse(fixture);
  assert.equal(Object.keys(parsed).length, 9, "Client has 8 nested domain objects plus id");
  assert.equal(parsed.identity.name, "Ada Lovelace");
  assert.equal(parsed.figures.documents[1].pct, null);
});

test("AI_clientRowSchema rejects a row missing a required field", () => {
  const fixture = makeClientRowFixture();
  delete fixture.identity;
  assert.throws(() => clientRowSchema.parse(fixture), /identity/);
});

test("AI_clientRowSchema rejects a figure field with the wrong type", () => {
  const fixture = makeClientRowFixture() as { figures: { performance: Array<{ pct: unknown }> } };
  fixture.figures.performance[0].pct = "not-a-number";
  assert.throws(() => clientRowSchema.parse(fixture), /pct/);
});

test("AI_readFigure reads a nested figure slot back out as a Figure object", () => {
  const row = clientRowSchema.parse(makeClientRowFixture()) as ClientRow;
  const figure = readFigure(row, "mand", 3);
  assert.deepEqual(figureSchema.parse(figure), {
    label: "mand label 3",
    value: "mand value 3",
    pct: 30,
    status: "ok",
  });
});

test("AI_kpiRowSchema parses a count_by tile", () => {
  const parsed = kpiRowSchema.parse({ bucket: "Compliant", label: "Compliant", count: 42 });
  assert.equal(parsed.count, 42);
});
