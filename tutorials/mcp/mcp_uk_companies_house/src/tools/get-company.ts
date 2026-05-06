import { z } from "zod";
import { type InferSchema, type ToolMetadata } from "xmcp";
import { companiesHouseGet, formatResult } from "../lib/companies-house-api";
import type {
  CompanyProfile,
  RegisteredOfficeAddress,
  InsolvencyResource,
  ChargeList,
} from "../types/companies-house";

const includeOptions = z.enum([
  "registered-office-address",
  "insolvency",
  "charges",
]);

export const schema = {
  companyNumber: z
    .string()
    .describe(
      "The Companies House company number, e.g. '00000006' or '12345678'. " +
        "Must include leading zeros exactly as registered."
    ),
  include: z
    .array(includeOptions)
    .optional()
    .describe(
      "Optional sub-resources to fetch alongside the company profile. " +
        "Values: 'registered-office-address' (full address details), " +
        "'insolvency' (insolvency case details), 'charges' (company charges/mortgages). " +
        "Each triggers an additional API call. Omit to fetch only the company profile."
    ),
};

export const metadata: ToolMetadata = {
  name: "get-company",
  description:
    "Get detailed information about a specific UK company from Companies House by its company number. " +
    "Always returns the core company profile (name, status, type, SIC codes, registered address summary, etc.). " +
    "Optionally include sub-resources: 'registered-office-address' for full address details, " +
    "'insolvency' for insolvency case details, 'charges' for company charges/mortgages.",
  annotations: {
    title: "Get Company",
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: true,
  },
};

export default async function getCompany({
  companyNumber,
  include,
}: Pick<InferSchema<typeof schema>, "companyNumber"> &
  Partial<InferSchema<typeof schema>>) {
  const basePath = `/company/${companyNumber}`;

  const profileResult = await companiesHouseGet<CompanyProfile>(basePath);
  if (!profileResult.ok) {
    return formatResult(profileResult);
  }

  const response: Record<string, unknown> = {
    profile: profileResult.data,
  };

  if (include && include.length > 0) {
    function fetchSubResource(resource: string) {
      switch (resource) {
        case "registered-office-address":
          return companiesHouseGet<RegisteredOfficeAddress>(
            `${basePath}/registered-office-address`
          );
        case "insolvency":
          return companiesHouseGet<InsolvencyResource>(
            `${basePath}/insolvency`
          );
        case "charges":
          return companiesHouseGet<ChargeList>(`${basePath}/charges`);
        default:
          return companiesHouseGet(`${basePath}/${resource}`);
      }
    }

    const fetches = include.map(async (resource) => {
      const result = await fetchSubResource(resource);
      return { resource, result };
    });

    const results = await Promise.allSettled(fetches);

    for (const settled of results) {
      if (settled.status === "fulfilled") {
        const { resource, result } = settled.value;
        response[resource] = result.ok ? result.data : { error: result.error };
      }
    }
  }

  return JSON.stringify(response, null, 2);
}
