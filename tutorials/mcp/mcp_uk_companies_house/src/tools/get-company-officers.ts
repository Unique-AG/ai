import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type {
  OfficerList,
  OfficerAppointmentDetails,
} from "../types/companies-house";

export const schema = {
  companyNumber: z
    .string()
    .describe(
      "The Companies House company number, e.g. '00000006' or '12345678'."
    ),
  appointmentId: z
    .string()
    .optional()
    .describe(
      "A specific officer appointment ID. When provided, returns details for that " +
        "single appointment instead of listing all officers. " +
        "The appointment ID can be found in the links of a list response."
    ),
  itemsPerPage: z
    .number()
    .optional()
    .describe(
      "Number of officers to return per page (list mode only)."
    ),
  startIndex: z
    .number()
    .optional()
    .describe(
      "The index of the first result to return, zero-based (list mode only)."
    ),
  registerType: z
    .string()
    .optional()
    .describe(
      "Filter by register type: 'directors', 'secretaries', or 'llp-members'. " +
        "Only used when listing officers (appointmentId not provided)."
    ),
  registerView: z
    .string()
    .optional()
    .describe(
      "Set to 'true' to show only officers on the company register. " +
        "Requires registerType to also be specified. List mode only."
    ),
  orderBy: z
    .string()
    .optional()
    .describe(
      "Sort order for the officer list: 'appointed_on', 'resigned_on', or 'surname'. " +
        "List mode only."
    ),
};

export const metadata: ToolMetadata = {
  name: "get-company-officers",
  description:
    "Get officer information for a UK company from Companies House. " +
    "Two modes: (1) List all officers — provide companyNumber only, with optional " +
    "pagination and filtering by registerType or orderBy. " +
    "(2) Get a single appointment — provide both companyNumber and appointmentId.",
  annotations: {
    title: "Get Company Officers",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function getCompanyOfficers(
  params: Pick<InferSchema<typeof schema>, "companyNumber"> &
    Partial<InferSchema<typeof schema>>
) {
  if (params.appointmentId) {
    const result = await companiesHouseGet<OfficerAppointmentDetails>(
      `/company/${params.companyNumber}/appointments/${params.appointmentId}`
    );
    return formatResult(result);
  }

  const result = await companiesHouseGet<OfficerList>(
    `/company/${params.companyNumber}/officers`,
    {
      items_per_page: params.itemsPerPage,
      start_index: params.startIndex,
      register_type: params.registerType,
      register_view: params.registerView,
      order_by: params.orderBy,
    }
  );
  return formatResult(result);
}
