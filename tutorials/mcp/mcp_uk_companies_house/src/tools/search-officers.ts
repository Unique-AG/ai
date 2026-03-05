import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type {
  OfficerSearchResult,
  OfficerAppointmentList,
} from "../types/companies-house";

export const schema = {
  query: z
    .string()
    .optional()
    .describe(
      "Search term for officer name. When provided, searches across all " +
        "Companies House officers. Mutually exclusive with 'officerId' — " +
        "provide one or the other, not both."
    ),
  officerId: z
    .string()
    .optional()
    .describe(
      "A specific officer ID (found in search results or officer list links). " +
        "When provided, returns all appointments for that officer across companies. " +
        "Mutually exclusive with 'query' — provide one or the other, not both."
    ),
  filter: z
    .string()
    .optional()
    .describe(
      "Filter for officer appointments. Set to 'active' to show only active " +
        "appointments. Only used with 'officerId'."
    ),
  itemsPerPage: z
    .number()
    .optional()
    .describe("Number of results to return per page."),
  startIndex: z
    .number()
    .optional()
    .describe(
      "The index of the first result to return, zero-based, for pagination."
    ),
};

export const metadata: ToolMetadata = {
  name: "search-officers",
  description:
    "Search for company officers or retrieve an officer's appointment history " +
    "from Companies House. Two modes: (1) Search — provide 'query' to search " +
    "officers by name. (2) Appointments — provide 'officerId' to list all of " +
    "that officer's appointments across companies. " +
    "Provide exactly one of 'query' or 'officerId'.",
  annotations: {
    title: "Search Officers",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function searchOfficers(
  params: Partial<InferSchema<typeof schema>>
) {
  if (!params.query && !params.officerId) {
    return "Error: You must provide either 'query' (to search officers) or 'officerId' (to list appointments). Neither was provided.";
  }

  if (params.query && params.officerId) {
    return "Error: Provide either 'query' or 'officerId', not both. Use 'query' to search by name, or 'officerId' to list a specific officer's appointments.";
  }

  if (params.query) {
    const result = await companiesHouseGet<OfficerSearchResult>("/search/officers", {
      q: params.query,
      items_per_page: params.itemsPerPage,
      start_index: params.startIndex,
    });
    return formatResult(result);
  }

  const result = await companiesHouseGet<OfficerAppointmentList>(
    `/officers/${params.officerId}/appointments`,
    {
      filter: params.filter,
      items_per_page: params.itemsPerPage,
      start_index: params.startIndex,
    }
  );
  return formatResult(result);
}
