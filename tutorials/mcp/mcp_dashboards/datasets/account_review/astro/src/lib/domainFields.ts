/**
 * Short filter / group-by aliases the dashboard sends, and the domain paths they
 * stand for.
 *
 * The MCP tools accept these aliases in `filters` and `ClientUpdate`, but a row
 * returned by `list_clients` is nested, so anything reading a value out of a row
 * has to expand the alias first.
 *
 * Kept in sync by hand with `FILTER_ALIASES` in
 * `datasets/account_review/fastmcp/constants.py`; that file maps the same aliases
 * onto storage columns. Both sides are checked against the TypeSpec contract
 * (`ClientFilter`, `ClientUpdate`) rather than against each other.
 */
export const DOMAIN_FIELD_ALIASES: Record<string, string> = {
  status: "case_action.status",
  risk_level: "compliance.risk_level",
  segment: "identity.segment",
  criticality: "compliance.criticality",
};

/** Expands a filter alias to its domain path; any other value passes through. */
export function domainPath(field: string): string {
  return DOMAIN_FIELD_ALIASES[field] ?? field;
}
