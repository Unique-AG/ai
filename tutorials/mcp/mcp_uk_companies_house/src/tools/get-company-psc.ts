import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type {
  Psc,
  PscList,
  PscStatementList,
} from "../types/companies-house";

const pscTypeEnum = z.enum([
  "individual",
  "individual-beneficial-owner",
  "corporate-entity",
  "legal-person",
]);

export const schema = {
  companyNumber: z
    .string()
    .describe(
      "The Companies House company number, e.g. '00000006' or '12345678'."
    ),
  pscId: z
    .string()
    .optional()
    .describe(
      "The ID of a specific Person with Significant Control. " +
        "When provided, 'type' is also required. " +
        "Found in the links of a PSC list response."
    ),
  type: pscTypeEnum
    .optional()
    .describe(
      "The type of PSC to retrieve. Required when 'pscId' is provided. " +
        "Values: 'individual' (natural person), " +
        "'individual-beneficial-owner' (natural person beneficial owner), " +
        "'corporate-entity' (company/corporate PSC), " +
        "'legal-person' (legal person PSC)."
    ),
  statements: z
    .boolean()
    .optional()
    .describe(
      "Set to true to retrieve PSC statements instead of the PSC list. " +
        "PSC statements are declarations about the company's PSC register status. " +
        "Ignored when 'pscId' is provided."
    ),
  itemsPerPage: z
    .number()
    .optional()
    .describe(
      "Number of results to return per page (list and statements mode only)."
    ),
  startIndex: z
    .number()
    .optional()
    .describe(
      "The index of the first result to return, zero-based (list and statements mode only)."
    ),
  registerView: z
    .string()
    .optional()
    .describe(
      "Set to 'true' to show only PSCs on the company register. " +
        "List and statements mode only."
    ),
};

export const metadata: ToolMetadata = {
  name: "get-company-psc",
  description:
    "Get Persons with Significant Control (PSC) data for a UK company from Companies House. " +
    "Three modes: (1) List all PSCs — provide companyNumber only. " +
    "(2) Get a specific PSC — provide companyNumber, pscId, and type " +
    "('individual', 'individual-beneficial-owner', 'corporate-entity', or 'legal-person'). " +
    "(3) List PSC statements — provide companyNumber and set statements=true.",
  annotations: {
    title: "Get Company PSC",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function getCompanyPsc(
  params: Pick<InferSchema<typeof schema>, "companyNumber"> &
    Partial<InferSchema<typeof schema>>
) {
  const basePath = `/company/${params.companyNumber}/persons-with-significant-control`;

  // Mode 1: Specific PSC by ID and type
  if (params.pscId) {
    if (!params.type) {
      return (
        "Error: When 'pscId' is provided, 'type' is also required. " +
        "Specify one of: 'individual', 'individual-beneficial-owner', " +
        "'corporate-entity', 'legal-person'."
      );
    }
    const result = await companiesHouseGet<Psc>(
      `${basePath}/${params.type}/${params.pscId}`
    );
    return formatResult(result);
  }

  // Mode 2: PSC statements
  if (params.statements) {
    const result = await companiesHouseGet<PscStatementList>(
      `/company/${params.companyNumber}/persons-with-significant-control-statements`,
      {
        items_per_page: params.itemsPerPage,
        start_index: params.startIndex,
        register_view: params.registerView,
      }
    );
    return formatResult(result);
  }

  // Mode 3: List all PSCs
  const result = await companiesHouseGet<PscList>(basePath, {
    items_per_page: params.itemsPerPage,
    start_index: params.startIndex,
    register_view: params.registerView,
  });
  return formatResult(result);
}
