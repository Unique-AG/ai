// Validated load of src/data/config.json — mcp_server / rm_name /
// page_title / poll_ms / connectors_online. Parsing it through zod here
// (once, at import time) means a typo'd or missing field in config.json
// fails the build immediately with a readable error, instead of silently
// rendering `undefined` into the page's <title>/greeting/connector count.
import { z } from "zod";
// The `with { type: "json" }` import attribute lets this module load under
// plain `node --test` as well as Astro/Vite's bundler — see cases.ts.
import configFile from "../data/config.json" with { type: "json" };

const dashboardConfigSchema = z.object({
  /** MCP server id the page's data-unique-source-server attributes bind to. */
  mcp_server: z.string(),
  /** Local mcp_sqlite_excel URL used only by the live-local build (see mode.ts). */
  mcp_local_url: z.string(),
  rm_name: z.string(),
  page_title: z.string(),
  /** How often bound lists re-poll, in milliseconds. */
  poll_ms: z.number().int().positive(),
  connectors_online: z.number().int().nonnegative(),
});

export type DashboardConfig = z.infer<typeof dashboardConfigSchema>;

export const config: DashboardConfig = dashboardConfigSchema.parse(configFile);
