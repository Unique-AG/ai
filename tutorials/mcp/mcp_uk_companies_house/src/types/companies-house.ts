/**
 * TypeScript type definitions for Companies House REST API responses.
 * Based on the official Companies House Public Data API.
 *
 * @see https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference
 */

// ---------------------------------------------------------------------------
// Shared / reusable types
// ---------------------------------------------------------------------------

/** Standard UK address used across many API resources. */
export interface Address {
  address_line_1?: string;
  address_line_2?: string;
  care_of?: string;
  country?: string;
  locality?: string;
  po_box?: string;
  postal_code?: string;
  premises?: string;
  region?: string;
}

/** Partial date (month + year), used for date_of_birth on officers/PSCs. */
export interface PartialDate {
  month: number;
  year: number;
  day?: number;
}

/** Self/related links object — keys vary per resource. */
export interface Links {
  self?: string;
  [key: string]: string | undefined;
}

// ---------------------------------------------------------------------------
// Company Profile  —  GET /company/{company_number}
// ---------------------------------------------------------------------------

export interface CompanyAccounts {
  accounting_reference_date?: { day: string; month: string };
  last_accounts?: {
    made_up_to?: string;
    type?: string;
    period_start_on?: string;
    period_end_on?: string;
  };
  next_accounts?: {
    due_on?: string;
    period_start_on?: string;
    period_end_on?: string;
    overdue?: boolean;
  };
  next_due?: string;
  next_made_up_to?: string;
  overdue?: boolean;
}

export interface ConfirmationStatement {
  last_made_up_to?: string;
  next_due?: string;
  next_made_up_to?: string;
  overdue?: boolean;
}

export interface PreviousCompanyName {
  ceased_on?: string;
  effective_from?: string;
  name?: string;
}

export interface CompanyProfile {
  company_name: string;
  company_number: string;
  company_status: string;
  company_status_detail?: string;
  type: string;
  subtype?: string;
  date_of_creation?: string;
  date_of_cessation?: string;
  registered_office_address?: Address;
  service_address?: Address;
  sic_codes?: string[];
  has_charges?: boolean;
  has_insolvency_history?: boolean;
  has_been_liquidated?: boolean;
  has_super_secure_pscs?: boolean;
  jurisdiction?: string;
  accounts?: CompanyAccounts;
  annual_return?: { last_made_up_to?: string; next_due?: string; overdue?: boolean };
  confirmation_statement?: ConfirmationStatement;
  links?: Links;
  etag?: string;
  registered_office_is_in_dispute?: boolean;
  undeliverable_registered_office_address?: boolean;
  can_file?: boolean;
  previous_company_names?: PreviousCompanyName[];
  last_full_members_list_date?: string;
  external_registration_number?: string;
  foreign_company_details?: Record<string, unknown>;
  branch_company_details?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Registered Office Address  —  GET /company/{company_number}/registered-office-address
// ---------------------------------------------------------------------------

export interface RegisteredOfficeAddress extends Address {
  kind?: string;
  etag?: string;
  links?: Links;
}

// ---------------------------------------------------------------------------
// Insolvency  —  GET /company/{company_number}/insolvency
// ---------------------------------------------------------------------------

export interface InsolvencyPractitioner {
  name?: string;
  address?: Address;
  appointed_on?: string;
  ceased_to_act_on?: string;
  role?: string;
}

export interface InsolvencyCase {
  type?: string;
  number?: number;
  dates?: Array<{ type?: string; date?: string }>;
  notes?: string[];
  practitioners?: InsolvencyPractitioner[];
  links?: Links;
}

export interface InsolvencyResource {
  etag?: string;
  cases?: InsolvencyCase[];
  status?: string[];
}

// ---------------------------------------------------------------------------
// Charges  —  GET /company/{company_number}/charges
// ---------------------------------------------------------------------------

export interface Charge {
  etag?: string;
  charge_code?: string;
  charge_number?: number;
  classification?: { type?: string; description?: string };
  status?: string;
  delivered_on?: string;
  created_on?: string;
  satisfied_on?: string;
  covering_instrument_date?: string;
  transactions?: Array<{
    delivered_on?: string;
    filing_type?: string;
    links?: Links;
  }>;
  particulars?: { type?: string; description?: string; contains_fixed_charge?: boolean; contains_floating_charge?: boolean; floating_charge_covers_all?: boolean; contains_negative_pledge?: boolean; chargor_acting_as_bare_trustee?: boolean };
  secured_details?: { type?: string; description?: string };
  scottish_alterations?: { type?: string; description?: string };
  persons_entitled?: Array<{ name?: string }>;
  links?: Links;
}

export interface ChargeList {
  etag?: string;
  items: Charge[];
  total_count: number;
  part_satisfied_count?: number;
  satisfied_count?: number;
  unfiltered_count?: number;
}

// ---------------------------------------------------------------------------
// Officers  —  GET /company/{company_number}/officers
// ---------------------------------------------------------------------------

export interface OfficerDateOfBirth extends PartialDate {}

export interface Officer {
  name: string;
  officer_role: string;
  appointed_on?: string;
  resigned_on?: string;
  nationality?: string;
  country_of_residence?: string;
  occupation?: string;
  date_of_birth?: OfficerDateOfBirth;
  address?: Address;
  links?: Links;
  identification?: {
    identification_type?: string;
    legal_authority?: string;
    legal_form?: string;
    place_registered?: string;
    registration_number?: string;
  };
  former_names?: Array<{ forenames?: string; surname?: string }>;
}

export interface OfficerList {
  etag?: string;
  items: Officer[];
  items_per_page: number;
  kind: string;
  start_index: number;
  total_results: number;
  active_count?: number;
  inactive_count?: number;
  resigned_count?: number;
  links?: Links;
}

// ---------------------------------------------------------------------------
// Single Officer Appointment  —  GET /company/{number}/appointments/{id}
// ---------------------------------------------------------------------------

export interface OfficerAppointmentDetails extends Officer {
  kind?: string;
  etag?: string;
}

// ---------------------------------------------------------------------------
// PSC  —  GET /company/{number}/persons-with-significant-control
// ---------------------------------------------------------------------------

export interface PscNameElements {
  title?: string;
  forename?: string;
  other_forenames?: string;
  middle_name?: string;
  surname?: string;
}

export interface PscIdentification {
  country_registered?: string;
  legal_authority?: string;
  legal_form?: string;
  place_registered?: string;
  registration_number?: string;
}

export interface Psc {
  name?: string;
  kind: string;
  natures_of_control?: string[];
  notified_on?: string;
  ceased_on?: string;
  ceased?: boolean;
  nationality?: string;
  country_of_residence?: string;
  date_of_birth?: PartialDate;
  name_elements?: PscNameElements;
  address?: Address;
  identification?: PscIdentification;
  links?: Links;
  etag?: string;
  description?: string;
}

export interface PscList {
  items: Psc[];
  items_per_page: number;
  start_index: number;
  total_results: number;
  active_count?: number;
  ceased_count?: number;
  links?: Links;
}

// ---------------------------------------------------------------------------
// PSC Statements  —  GET /company/{number}/persons-with-significant-control-statements
// ---------------------------------------------------------------------------

export interface PscStatement {
  statement: string;
  kind?: string;
  notified_on?: string;
  ceased_on?: string;
  ceased?: boolean;
  links?: Links;
  etag?: string;
}

export interface PscStatementList {
  items: PscStatement[];
  items_per_page: number;
  start_index: number;
  total_results: number;
  active_count?: number;
  ceased_count?: number;
  links?: Links;
}

// ---------------------------------------------------------------------------
// Filing History  —  GET /company/{number}/filing-history
// ---------------------------------------------------------------------------

export interface FilingAnnotation {
  annotation?: string;
  category?: string;
  date?: string;
  description?: string;
  description_values?: Record<string, string>;
  type?: string;
}

export interface AssociatedFiling {
  category?: string;
  date?: string;
  description?: string;
  description_values?: Record<string, string>;
  type?: string;
  action_date?: string;
}

export interface FilingResolution {
  category?: string;
  description?: string;
  description_values?: Record<string, string>;
  document_id?: string;
  receive_date?: string;
  subcategory?: string;
  type?: string;
}

export interface Filing {
  transaction_id: string;
  type: string;
  date: string;
  description: string;
  category: string;
  subcategory?: string;
  description_values?: Record<string, string>;
  action_date?: string;
  pages?: number;
  barcode?: string;
  paper_filed?: boolean;
  links?: Links;
  annotations?: FilingAnnotation[];
  associated_filings?: AssociatedFiling[];
  resolutions?: FilingResolution[];
}

export interface FilingHistoryList {
  items: Filing[];
  items_per_page: number;
  start_index: number;
  total_count: number;
  filing_history_status?: string;
}

// ---------------------------------------------------------------------------
// Company Search  —  GET /search/companies
// ---------------------------------------------------------------------------

export interface CompanySearchItem {
  company_name: string;
  company_number: string;
  company_status: string;
  company_type: string;
  company_subtype?: string;
  date_of_creation?: string;
  date_of_cessation?: string;
  registered_office_address?: Address;
  sic_codes?: string[];
  snippet?: string;
  title?: string;
  address_snippet?: string;
  description?: string;
  description_identifier?: string[];
  matches?: Record<string, number[]>;
  kind?: string;
  links?: Links;
  external_registration_number?: string;
}

export interface CompanySearchResult {
  items: CompanySearchItem[];
  items_per_page: number;
  start_index: number;
  total_results: number;
  kind?: string;
  page_number?: number;
}

// ---------------------------------------------------------------------------
// Advanced Company Search  —  GET /advanced-search/companies
// ---------------------------------------------------------------------------

export interface AdvancedCompanySearchResult {
  items: CompanySearchItem[];
  top_hit?: CompanySearchItem;
  hits: number;
  items_per_page: number;
  start_index: number;
  total_results?: number;
  kind?: string;
}

// ---------------------------------------------------------------------------
// Officer Search  —  GET /search/officers
// ---------------------------------------------------------------------------

export interface OfficerSearchItem {
  title: string;
  address_snippet?: string;
  address?: Address;
  appointment_count?: number;
  date_of_birth?: PartialDate;
  description?: string;
  description_identifiers?: string[];
  kind?: string;
  links?: Links;
  matches?: Record<string, number[]>;
  snippet?: string;
}

export interface OfficerSearchResult {
  items: OfficerSearchItem[];
  items_per_page: number;
  start_index: number;
  total_results: number;
  kind?: string;
  page_number?: number;
}

// ---------------------------------------------------------------------------
// Officer Appointments  —  GET /officers/{officer_id}/appointments
// ---------------------------------------------------------------------------

export interface OfficerAppointmentItem {
  name?: string;
  name_elements?: { title?: string; forename?: string; other_forenames?: string; surname?: string; honours?: string };
  officer_role: string;
  appointed_on?: string;
  appointed_before?: string;
  resigned_on?: string;
  nationality?: string;
  country_of_residence?: string;
  occupation?: string;
  address?: Address;
  appointed_to?: { company_name?: string; company_number?: string; company_status?: string };
  is_pre_1992_appointment?: boolean;
  links?: Links;
  identification?: {
    identification_type?: string;
    legal_authority?: string;
    legal_form?: string;
    place_registered?: string;
    registration_number?: string;
  };
}

export interface OfficerAppointmentList {
  items: OfficerAppointmentItem[];
  items_per_page: number;
  start_index: number;
  total_results: number;
  is_corporate_officer?: boolean;
  name?: string;
  date_of_birth?: PartialDate;
  kind?: string;
  links?: Links;
}
