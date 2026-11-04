"""Typed FastMCP app for the account_review dataset.

Tools are hand-written against the models generated from
`../contract/main.tsp` — there is no shared CRUD helper to inherit from. See
`docs/architecture.md` for why, and for the domain/storage mapping this package
owns.

Tools that only touch SQLite are declared `def` so FastMCP runs them in a
worker thread. Tools that elicit (`update_client` status changes, `draft_client_email`,
`send_email`) are `async def` because they await MCP elicitation.

Run with::

    python datasets/account_review/fastmcp/app.py
"""

from __future__ import annotations

import logging

import paths as _paths  # noqa: F401
import mcp_tools as _mcp_tools  # noqa: F401 — register MCP tools on import
from admin_site import register_admin_routes
from constants import logger
from domain import (
    client_from_row as _client_from_row,
    empty_figure_groups as _empty_figure_groups,
)
from email_drafts import (
    default_email_draft as _default_email_draft,
    email_draft_elicit_model as _email_draft_elicit_model,
    email_str as _email_str,
    elicit_email_draft as _elicit_email_draft,
    send_email_payload as _send_email_payload,
)
from generated.models import (
    Audience,
    DashboardFigures,
    OutboundEmailDraft,
    Status,
)
from mcp_tools import send_email
from runtime import (
    allowed_hosts,
    bind_host_and_port,
    custom_middleware,
    mcp,
    repo,
    server_settings,
    settings,
)

register_admin_routes(mcp, repo=repo, settings=settings, dataset="account_review")

# Re-exports used by tests / the server.py shim.
__all__ = [
    "Audience",
    "DashboardFigures",
    "OutboundEmailDraft",
    "Status",
    "_client_from_row",
    "_default_email_draft",
    "_elicit_email_draft",
    "_email_draft_elicit_model",
    "_email_str",
    "_empty_figure_groups",
    "_mcp_tools",
    "_send_email_payload",
    "main",
    "mcp",
    "repo",
    "send_email",
    "settings",
]


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    host, port = bind_host_and_port()
    logger.info(
        "Starting account_review MCP with db=%s excel=%s host=%s port=%s",
        repo.db_path,
        repo.excel_path,
        host,
        port,
    )
    repo.ensure_ready()
    mcp.run(
        transport=server_settings.transport_scheme,
        host=host,
        port=port,
        log_level="info",
        middleware=custom_middleware,
        allowed_hosts=allowed_hosts(),
    )


if __name__ == "__main__":
    main()
