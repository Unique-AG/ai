// Field-grid definitions for each client-detail section — keeps markup in
// ClientDetailPage.astro declarative while the column choices live here,
// typed against ClientRow (see lib/schema.ts + the real Excel "clients"
// sheet dumped by scripts/dump_mock_data.py).
import type { Field } from "../lib/fields";

export const executiveSummaryFields: Field[] = [
  { label: "Rule code", field: "case_action.rule_code", code: true },
  { label: "Due", field: "case_action.due_date", na: true },
];

export const identityFields: Field[] = [
  { label: "Full name", field: "identity.name" },
  { label: "Client type", field: "identity.type" },
  { label: "Date of birth", field: "contact.date_of_birth", na: true },
  { label: "Occupation", field: "contact.occupation", na: true },
  { label: "Marital status", field: "contact.marital_status", na: true },
  { label: "Nationality", field: "contact.nationality" },
  { label: "Country of residence", field: "contact.residence" },
  { label: "Domicile / tax residence", field: "contact.domicile" },
  { label: "Incorporation", field: "contact.incorporation", na: true },
  { label: "Residential address", field: "contact.residential_address", na: true },
  { label: "Email", field: "contact.email", na: true },
  { label: "Phone", field: "contact.phone", na: true },
  { label: "Client reference", field: "identity.crd_number", code: true },
  { label: "Onboarded", field: "portfolio.onboarded" },
];

export const historyFields: Field[] = [
  { label: "Last reviewed", field: "review_schedule.last_reviewed" },
  { label: "Next review due", field: "review_schedule.next_review_due" },
  { label: "KYC refresh due", field: "review_schedule.kyc_refresh_due" },
];

export const docsKycFields: Field[] = [
  { label: "PEP status", field: "compliance.pep" },
  { label: "Adverse media", field: "compliance.adverse_media" },
  { label: "Sanctions", field: "compliance.sanctions" },
  { label: "US Person (FATCA)", field: "compliance.fatca_us_person" },
  { label: "Verification source", field: "compliance.verification_source" },
];

export const holdingsFields: Field[] = [
  { label: "Client categorization", field: "compliance.client_categorization" },
  { label: "Category required", field: "compliance.category_required", na: true },
  { label: "Category review status", field: "compliance.category_review_status" },
];

export const suitabilityFields: Field[] = [
  { label: "Risk tolerance", field: "compliance.risk_tolerance" },
  { label: "Investment horizon", field: "suitability.investment_horizon" },
  { label: "Knowledge & experience", field: "suitability.knowledge_experience" },
  { label: "Last suitability test", field: "suitability.last_suitability_test" },
  { label: "Outcome", field: "suitability.suitability_outcome" },
];
