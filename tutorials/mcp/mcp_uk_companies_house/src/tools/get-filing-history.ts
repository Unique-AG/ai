import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type { Filing, FilingHistoryList } from "../types/companies-house";

export const schema = {
  companyNumber: z
    .string()
    .describe(
      "The Companies House company number, e.g. '00000006' or '12345678'."
    ),
  transactionId: z
    .string()
    .optional()
    .describe(
      "A specific filing transaction ID. When provided, returns full details " +
        "for that single filing instead of the filing history list. " +
        "Found in the links of a filing history list response."
    ),
  category: z
    .string()
    .optional()
    .describe(
      "Filter filing history by category. Comma-separated values: " +
        "'accounts', 'annual-return', 'capital', 'change-of-name', " +
        "'confirmation-statement', 'incorporation', 'liquidation', " +
        "'mortgage', 'officers', 'resolution', 'address'. " +
        "Only used when listing (transactionId not provided)."
    ),
  itemsPerPage: z
    .number()
    .optional()
    .describe(
      "Number of filings to return per page (list mode only). Default is 25."
    ),
  startIndex: z
    .number()
    .optional()
    .describe(
      "The index of the first result to return, zero-based (list mode only)."
    ),
};

export const metadata: ToolMetadata = {
  name: "get-filing-history",
  description:
    "Get filing history for a UK company from Companies House. " +
    "Two modes: (1) List filings — provide companyNumber with optional category " +
    "filter and pagination. (2) Get a single filing — provide both companyNumber " +
    "and transactionId for full filing details.",
  annotations: {
    title: "Get Filing History",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function getFilingHistory(
  params: Pick<InferSchema<typeof schema>, "companyNumber"> &
    Partial<InferSchema<typeof schema>>
) {
  const basePath = `/company/${params.companyNumber}/filing-history`;

  if (params.transactionId) {
    const result = await companiesHouseGet<Filing>(
      `${basePath}/${params.transactionId}`
    );
    return formatResult(result);
  }

  const result = await companiesHouseGet<FilingHistoryList>(basePath, {
    category: params.category,
    items_per_page: params.itemsPerPage,
    start_index: params.startIndex,
  });
  return formatResult(result);
}
