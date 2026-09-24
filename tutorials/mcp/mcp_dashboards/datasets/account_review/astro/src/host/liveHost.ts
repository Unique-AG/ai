/**
 * `live-local` entry point for the account_review dashboard.
 *
 * All the behaviour lives in the shared host; the only dataset-specific part is
 * which generated schema validates which tool's response. Register every tool
 * the page binds to, so a drift between the Python and TypeScript sides of the
 * contract surfaces on the page instead of as a blank panel.
 */
import { startLiveHost } from "@mcp-dashboards/host/liveHost.ts";

import { zClient, zClientEmailDraftResult, zClientListResult, zCountByResult, zSendEmailResult } from "../lib/generated/zod.gen.ts";

startLiveHost({
  toolResultSchemas: {
    list_clients: zClientListResult,
    count_clients_by: zCountByResult,
    portfolio_kpis: zCountByResult,
    update_client: zClient,
    draft_client_email: zClientEmailDraftResult,
    send_email: zSendEmailResult,
  },
});
