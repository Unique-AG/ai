import "@typespec/http";
import "@typespec/rest";
import "@typespec/openapi3";

using TypeSpec.Http;

@service(#{ title: "Account Review MCP Dashboard Contract" })
@doc("Typed domain contract for the account review MCP server and Astro dashboard.")
namespace AccountReview;

alias NullableString = string | null;
alias NullableNumber = float64 | null;
alias ReviewStatus =
  | "Compliant"
  | "Escalated"
  | "Screening hit"
  | "Deadline approaching"
  | "Limit exceeded"
  | "Review required"
  | "Regulatory breach"
  | "Regulatory change";
alias RiskLevel = "Low" | "Medium" | "High";
alias ClientSegment = "Corporate / Holding" | "Private Wealth";
alias ClientType = "Company" | "Individual";
alias YesNo = "Yes" | "No";

@doc("Calendar date serialized as ISO 8601 full-date text.")
@format("date")
scalar IsoDate extends string;

@doc("Three-letter ISO 4217 currency code used for portfolio values.")
@pattern("^[A-Z]{3}$")
scalar CurrencyCode extends string;

@doc("Email address for a client or contact person.")
@format("email")
scalar EmailAddress extends string;

@doc("Stable source-system reference for a client.")
@minLength(1)
scalar ClientReference extends string;

@doc("Sort instruction accepted by list-style tools.")
model SortSpec {
  @doc("Domain field path, for example identity.name or compliance.risk_level.")
  field: string;

  @doc("Sort direction. Defaults to ascending when omitted.")
  dir?: "asc" | "desc";
}

@doc("Client identity, source reference, legal form, and dashboard segment.")
model ClientIdentity {
  @doc("Display name shown in the dashboard.")
  @minLength(1)
  name: string;

  @doc("Stable client reference from the source workbook or upstream system.")
  reference: ClientReference;

  @doc("Regulatory CRD or internal registration number.")
  @minLength(1)
  crd_number: string;

  @doc("Client legal form represented in the dataset.")
  type: ClientType;

  @doc("Commercial segment used for portfolio grouping and filtering.")
  segment: ClientSegment;
}

@doc("Personal, contact, and residency information for a client.")
model ClientContact {
  @doc("Date of birth for individuals, when available.")
  date_of_birth?: IsoDate | null;

  @doc("Occupation or business role supplied in the workbook.")
  occupation?: NullableString;

  @doc("Marital status for individual clients, when available.")
  marital_status?: NullableString;

  @doc("Client nationality.")
  nationality?: NullableString;

  @doc("Country or jurisdiction of residence.")
  residence?: NullableString;

  @doc("Country or jurisdiction of domicile.")
  domicile?: NullableString;

  @doc("Company incorporation jurisdiction, when applicable.")
  incorporation?: NullableString;

  @doc("Residential or registered address text.")
  residential_address?: NullableString;

  @doc("Primary email address.")
  email?: EmailAddress | null;

  @doc("Primary phone number as supplied by the source workbook.")
  phone?: NullableString;
}

@doc("Portfolio-level values displayed in the dashboard.")
model PortfolioSummary {
  @doc("Date the client relationship was onboarded.")
  onboarded: IsoDate;

  @doc("Currency for the portfolio value.")
  currency: CurrencyCode;

  @doc("Portfolio market value in the declared currency.")
  @minValue(0)
  value: float64;
}

@doc("Compliance, KYC, and regulatory assessment fields.")
model ComplianceProfile {
  @doc("Overall compliance risk bucket.")
  risk_level: RiskLevel;

  @doc("Investment risk profile recorded for the client.")
  risk_profile: string;

  @doc("Risk tolerance recorded for suitability review.")
  risk_tolerance: string;

  @doc("Operational criticality used by review queues.")
  criticality: string;

  @doc("Whether the client is marked as politically exposed.")
  pep: YesNo;

  @doc("Whether adverse media is present.")
  adverse_media: YesNo;

  @doc("Whether sanctions exposure is present.")
  sanctions: YesNo;

  @doc("Whether FATCA US-person status is indicated.")
  fatca_us_person: YesNo;

  @doc("Verification source or source-of-wealth evidence.")
  verification_source: string;

  @doc("Comma-separated document identifiers available for the client.")
  documents_on_file: string;

  @doc("Mandate description as supplied by the source workbook.")
  mandate_type: string;

  @doc("MiFID or client categorization label.")
  client_categorization: string;

  @doc("Category reassessment requirement, when applicable.")
  category_required?: NullableString;

  @doc("Current categorization review status.")
  category_review_status: string;
}

@doc("Review dates used for KYC and suitability scheduling.")
model ReviewSchedule {
  @doc("Date of the most recent completed review.")
  last_reviewed: IsoDate;

  @doc("Next scheduled relationship review date.")
  next_review_due: IsoDate;

  @doc("Next KYC refresh due date.")
  kyc_refresh_due: IsoDate;
}

@doc("Suitability assessment details for the client portfolio.")
model SuitabilityProfile {
  @doc("Investment horizon label from the source workbook.")
  investment_horizon: string;

  @doc("Knowledge and experience assessment.")
  knowledge_experience: string;

  @doc("Date of the most recent suitability test.")
  last_suitability_test: IsoDate;

  @doc("Outcome summary for the latest suitability review.")
  suitability_outcome: string;
}

@doc("Workflow action state and recommended next step for the client.")
model CaseAction {
  @doc("Current workflow status for the review case.")
  status: ReviewStatus;

  @doc("Rule identifier that triggered the action, when applicable.")
  rule_code?: NullableString;

  @doc("Open issue description shown to reviewers.")
  open_issue?: NullableString;

  @doc("Recommended remediation or reviewer action.")
  recommended_action?: NullableString;

  @doc("ISO 8601 due date for the open remediation action, when applicable.")
  due_date?: IsoDate | null;

  @doc("Short action title displayed in the case action bar.")
  title?: NullableString;

  @doc("Long-form action explanation for reviewers.")
  explanation?: NullableString;

  @doc("Button label used by the dashboard action.")
  button_label?: NullableString;

  @doc("Button target or tool hint used by the dashboard action.")
  button_target?: NullableString;

  @doc("Owner responsible for follow-up.")
  owner?: NullableString;

  @doc("Subscription/transaction amount under Source of Funds review, in the case currency.")
  sof_transaction_amount?: NullableNumber;

  @doc("Knowledge-base folder id scoping Internal Search for this case's supporting evidence.")
  sof_folder_id?: NullableString;
}

@doc("Small dashboard metric used in client figures.")
model FigureMetric {
  @doc("Metric label.")
  label?: NullableString;

  @doc("Metric display value.")
  value?: NullableString;

  @doc("Metric percentage value, when available.")
  pct?: NullableNumber;

  @doc("Metric status text or severity marker.")
  status?: NullableString;
}

@doc("Grouped dashboard figures shown on the client detail cards.")
model DashboardFigures {
  @doc("Document and evidence metrics.")
  documents: FigureMetric[];

  @doc("Performance-related metrics.")
  performance: FigureMetric[];

  @doc("Mandate and suitability metrics.")
  mandate: FigureMetric[];

  @doc("Holdings and portfolio composition metrics.")
  holdings: FigureMetric[];
}

@doc("Nested domain representation consumed by the FastMCP tools and Astro dashboard.")
model Client {
  @doc("Dataset-local primary key.")
  id: int32;

  @doc("Identity and segmentation fields.")
  identity: ClientIdentity;

  @doc("Contact and residency fields.")
  contact: ClientContact;

  @doc("Portfolio summary fields.")
  portfolio: PortfolioSummary;

  @doc("Compliance and regulatory profile.")
  compliance: ComplianceProfile;

  @doc("Review schedule fields.")
  review_schedule: ReviewSchedule;

  @doc("Suitability assessment fields.")
  suitability: SuitabilityProfile;

  @doc("Workflow action fields.")
  case_action: CaseAction;

  @doc("Dashboard figure groups.")
  figures: DashboardFigures;
}

@doc("Payload for creating a client from typed dashboard or MCP input.")
model ClientCreate {
  identity: ClientIdentity;
  contact: ClientContact;
  portfolio: PortfolioSummary;
  compliance: ComplianceProfile;
  review_schedule: ReviewSchedule;
  suitability: SuitabilityProfile;
  case_action: CaseAction;
}

@doc("Patch payload for workflow fields that the dashboard edits inline.")
model ClientUpdate {
  @doc("New workflow status.")
  status?: ReviewStatus;

  @doc("New compliance risk level.")
  risk_level?: RiskLevel;
}

@doc("Supported typed filters for client list tools.")
model ClientFilter {
  @doc("Filter by workflow status.")
  status?: ReviewStatus;

  @doc("Filter by compliance risk level.")
  risk_level?: RiskLevel;

  @doc("Filter by commercial segment.")
  segment?: ClientSegment;

  @doc("Filter by operational criticality.")
  criticality?: string;

  @doc("When true, exclude Compliant clients (attention rail).")
  needs_attention?: boolean;
}

/** Who an outbound remediation email is addressed to. */
alias EmailAudience = "client" | "compliance";

@doc("Email draft the RM reviews before sending outside the platform.")
model OutboundEmailDraft {
  @doc("Whether this email goes to the client or to Compliance.")
  audience: EmailAudience;

  @doc("Recipient email address.")
  to: EmailAddress;

  @doc("Email subject line.")
  subject: string;

  @doc("Email body text.")
  body: string;

  @doc("Optional new workflow status to apply after the email is accepted.")
  new_status?: ReviewStatus;
}

@doc("Result of drafting an email via MCP elicitation without sending.")
model ClientEmailDraftResult {
  @doc("Client row after any accepted status update.")
  client: Client;

  @doc("Accepted email draft contents.")
  draft: OutboundEmailDraft;

  @doc("True when case_action.status was updated as part of this draft.")
  status_updated: boolean;
}

@doc("Result of attempting to send an email after the RM reviews the draft.")
model SendEmailResult {
  @doc("Client row after any accepted status update.")
  client: Client;

  @doc("Email contents reviewed by the RM (present whether or not delivery was confirmed).")
  draft: OutboundEmailDraft;

  @doc("True when the RM confirmed send; false when draft review or send confirmation was cancelled.")
  sent: boolean;

  @doc("True when case_action.status was updated as part of a confirmed send.")
  status_updated: boolean;

  @doc("Simulated outbound message id when sent; null when not sent (demo facade, no real SMTP).")
  message_id?: string | null;

  @doc("Human-readable delivery outcome the agent must relay: whether the mail was sent or not.")
  delivery_message: string;
}

@doc("Search, filter, sort, and pagination request for listing clients.")
model ClientListRequest {
  @doc("Structured filters mapped onto the source SQLite columns.")
  filters?: ClientFilter;

  @doc("Full-text search phrase applied to selected display fields.")
  search?: string;

  @doc("Ordered sort fields.")
  sort?: SortSpec[];

  @doc("Maximum number of rows to return.")
  @minValue(1)
  limit?: int32;

  @doc("Number of matching rows to skip.")
  @minValue(0)
  offset?: int32;
}

@doc("Paginated client list response.")
model ClientListResult {
  @doc("Source table name.")
  table: string;

  @doc("Number of rows returned in this response.")
  count: int32;

  @doc("Total rows matching the filters before pagination.")
  total_matching: int32;

  @doc("Requested page size.")
  limit: int32;

  @doc("Requested offset.")
  offset: int32;

  @doc("Client rows for this page.")
  rows: Client[];
}

@doc("Single bucket returned by a count-by aggregation.")
model CountByRow {
  @doc("Raw bucket value.")
  bucket: string;

  @doc("Display label for the bucket.")
  label: string;

  @doc("Number of matching clients.")
  count: int32;
}

@doc("Count-by aggregation response for dashboard KPI tiles.")
model CountByResult {
  @doc("Source table name.")
  table: string;

  @doc("Domain or source column used for grouping.")
  column: string;

  @doc("Total rows counted.")
  total: int32;

  @doc("Raw bucket-to-count mapping.")
  counts: Record<int32>;

  @doc("Ordered rows suitable for dashboard rendering.")
  rows: CountByRow[];
}

@route("/clients")
@doc("Operations mirrored by the typed account-review FastMCP tools.")
interface Clients {
  @get
  @summary("List clients")
  @doc("Return a paginated client list with optional search terms.")
  op list(@query search?: string, @query limit?: int32, @query offset?: int32): ClientListResult;

  @post
  @route("/search")
  @summary("Search clients")
  @doc("Return clients using structured filters, search, sort, and pagination.")
  op search(@body request: ClientListRequest): ClientListResult;

  @get
  @route("/count-by")
  @summary("Count clients by field")
  @doc("Aggregate clients by a supported domain field such as case_action.status.")
  op countBy(@query column?: string): CountByResult;

  @get
  @route("/{id}")
  @summary("Get client")
  @doc("Return one client by dataset-local primary key.")
  op get(@path id: int32): Client;

  @post
  @summary("Create client")
  @doc("Create a client using the typed domain payload.")
  op create(@body client: ClientCreate): Client;

  @patch
  @route("/{id}")
  @summary("Update client workflow fields")
  @doc("Patch the editable workflow fields for a client.")
  op update(@path id: int32, @body fields: ClientUpdate): Client;

  @post
  @route("/{id}/email-draft")
  @summary("Draft email")
  @doc("Elicit an email draft to the client or Compliance, optionally update status, without sending.")
  op draftEmail(@path id: int32, @query audience?: EmailAudience): ClientEmailDraftResult;

  @post
  @route("/{id}/email-send")
  @summary("Send email")
  @doc("Elicit and review an email draft to the client or Compliance, confirm send, then report whether delivery succeeded (simulated facade). Always returns sent true/false with delivery_message — never leave the outcome ambiguous.")
  op sendEmail(@path id: int32, @query audience: EmailAudience): SendEmailResult;
}
