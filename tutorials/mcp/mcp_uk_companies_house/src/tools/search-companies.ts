import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type {
  CompanySearchResult,
  AdvancedCompanySearchResult,
} from "../types/companies-house";

export const schema = {
  query: z
    .string()
    .optional()
    .describe(
      "Search term for company name. When provided, uses the basic search endpoint. " +
        "Omit this and use the advanced filters below for more precise searches."
    ),
  companyNameIncludes: z
    .string()
    .optional()
    .describe(
      "Advanced search: company name must include this text. " +
        "Only used when 'query' is not provided."
    ),
  companyNameExcludes: z
    .string()
    .optional()
    .describe(
      "Advanced search: company name must NOT include this text. " +
        "Only used when 'query' is not provided."
    ),
  companyStatus: z
    .string()
    .optional()
    .describe(
      "Advanced search: filter by status. Comma-separated values: " +
        "'active', 'dissolved', 'liquidation', 'receivership', 'converted-closed', " +
        "'voluntary-arrangement', 'insolvency-proceedings', 'administration', 'open', 'closed'. " +
        "Only used when 'query' is not provided."
    ),
  companySubtype: z
    .string()
    .optional()
    .describe(
      "Advanced search: filter by company subtype, e.g. 'community-interest-company', " +
        "'private-fund-limited-partnership'. Only used when 'query' is not provided."
    ),
  companyType: z
    .string()
    .optional()
    .describe(
      "Advanced search: filter by company type. Comma-separated values: " +
        "'ltd', 'plc', 'llp', 'limited-partnership', 'scottish-partnership', " +
        "'royal-charter', 'registered-society-non-jurisdictional'. " +
        "Only used when 'query' is not provided."
    ),
  dissolvedFrom: z
    .string()
    .optional()
    .describe(
      "Advanced search: dissolved on or after this date (YYYY-MM-DD). " +
        "Only used when 'query' is not provided."
    ),
  dissolvedTo: z
    .string()
    .optional()
    .describe(
      "Advanced search: dissolved on or before this date (YYYY-MM-DD). " +
        "Only used when 'query' is not provided."
    ),
  incorporatedFrom: z
    .string()
    .optional()
    .describe(
      "Advanced search: incorporated on or after this date (YYYY-MM-DD). " +
        "Only used when 'query' is not provided."
    ),
  incorporatedTo: z
    .string()
    .optional()
    .describe(
      "Advanced search: incorporated on or before this date (YYYY-MM-DD). " +
        "Only used when 'query' is not provided."
    ),
  location: z
    .string()
    .optional()
    .describe(
      "Advanced search: filter by registered office location. " +
        "Only used when 'query' is not provided."
    ),
  sicCodes: z
    .string()
    .optional()
    .describe(
      "Advanced search: filter by SIC codes. Comma-separated, e.g. '01110,62020'. " +
        "Only used when 'query' is not provided."
    ),
  itemsPerPage: z
    .number()
    .optional()
    .describe(
      "Number of results to return per page. " +
        "For basic search, default is 20. For advanced search, range 1-5000."
    ),
  startIndex: z
    .number()
    .optional()
    .describe(
      "The index of the first result to return (zero-based), for pagination."
    ),
};

export const metadata: ToolMetadata = {
  name: "search-companies",
  description:
    "Search for UK companies on Companies House. Supports two modes: " +
    "(1) Basic search — provide 'query' to search by company name. " +
    "(2) Advanced search — omit 'query' and use filters like companyNameIncludes, " +
    "companyStatus, companyType, location, sicCodes, incorporatedFrom/To, dissolvedFrom/To. " +
    "Use basic search for quick lookups, advanced search for precise filtering.",
  annotations: {
    title: "Search Companies",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function searchCompanies(
  params: Partial<InferSchema<typeof schema>>
) {
  console.log(`[search-companies] received params: ${JSON.stringify(params)}`);
  if (params.query) {
    const result = await companiesHouseGet<CompanySearchResult>("/search/companies", {
      q: params.query,
      items_per_page: params.itemsPerPage,
      start_index: params.startIndex,
    });
    return formatResult(result);
  }

  const result = await companiesHouseGet<AdvancedCompanySearchResult>("/advanced-search/companies", {
    company_name_includes: params.companyNameIncludes,
    company_name_excludes: params.companyNameExcludes,
    company_status: params.companyStatus,
    company_subtype: params.companySubtype,
    company_type: params.companyType,
    dissolved_from: params.dissolvedFrom,
    dissolved_to: params.dissolvedTo,
    incorporated_from: params.incorporatedFrom,
    incorporated_to: params.incorporatedTo,
    location: params.location,
    sic_codes: params.sicCodes,
    size: params.itemsPerPage,
    start_index: params.startIndex,
  });
  return formatResult(result);
}
