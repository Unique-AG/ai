import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from db_tool_reconciliation import service as reconciliation_service
from db_tool_reconciliation.prompts import (
    GET_COUNTERPARTY_EMAIL_CASHFLOWS_DESCRIPTION,
    GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION,
    MATCH_CASHFLOWS_DESCRIPTION,
    SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION,
)

load_dotenv()

ZITADEL_URL = os.getenv("ZITADEL_URL", "https://id.unique.app")

# Must match the upstream client used by the OAuthProxy below so the
# token introspection call authenticates as the same Zitadel client.
upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")
base_url_arg = sys.argv[1] if len(sys.argv) > 1 else base_url_env

token_verifier = IntrospectionTokenVerifier(
    introspection_url=f"{ZITADEL_URL}/oauth/v2/introspect",
    client_id=upstream_client_id,
    client_secret=upstream_client_secret,
    client_auth_method="client_secret_basic",
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=upstream_client_id,
    upstream_client_secret=upstream_client_secret,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=base_url_arg,
    redirect_path=None,
    issuer_url=None,
    service_documentation_url=None,
    allowed_client_redirect_uris=None,
    valid_scopes=["email", "openid", "profile"],
    forward_pkce=True,
    token_endpoint_auth_method="client_secret_post",
    extra_authorize_params=None,
    extra_token_params=None,
)

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp = FastMCP("Trade Reconciliation 🚀", auth=auth)


@mcp.tool(
    name="Get_Customer_Book_Cashflows",
    title="Customer (book) cash flows",
    description=GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION,
    meta={
        "unique.app/icon": "database",
        "unique.app/system-prompt": GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION,
    },
)
async def get_customer_book_cashflows(
    counterparty: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Optional ILIKE filter on the counterparty column (e.g. "
                "'Goldman%')."
            ),
        ),
    ] = None,
    ccy: Annotated[
        str | None,
        Field(default=None, description="Optional currency filter (USD, EUR, ...)."),
    ] = None,
    side: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional side filter: BUY, SELL, SHORT SELL, BUY TO COVER.",
        ),
    ] = None,
    trade_date: Annotated[
        str | None,
        Field(default=None, description="Optional ISO trade date (YYYY-MM-DD)."),
    ] = None,
    settl_date: Annotated[
        str | None,
        Field(default=None, description="Optional ISO settlement date (YYYY-MM-DD)."),
    ] = None,
    instrument: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional ILIKE filter on the instrument column.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(default=200, ge=1, le=2000, description="Maximum number of rows to return."),
    ] = 200,
) -> str:
    rows = reconciliation_service.list_customer_book_cashflows(
        counterparty=counterparty,
        ccy=ccy,
        side=side,
        trade_date=trade_date,
        settl_date=settl_date,
        instrument=instrument,
        limit=limit,
    )
    return json.dumps({"count": len(rows), "rows": rows}, default=str)


@mcp.tool(
    name="Get_Counterparty_Email_Cashflows",
    title="Counterparty (email) cash flows",
    description=GET_COUNTERPARTY_EMAIL_CASHFLOWS_DESCRIPTION,
    meta={
        "unique.app/icon": "mail",
        "unique.app/system-prompt": GET_COUNTERPARTY_EMAIL_CASHFLOWS_DESCRIPTION,
    },
)
async def get_counterparty_email_cashflows(
    vendor: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional ILIKE filter on the vendor column.",
        ),
    ] = None,
    ccy: Annotated[
        str | None,
        Field(default=None, description="Optional currency filter (USD, EUR, ...)."),
    ] = None,
    action: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional action filter: BUY, SELL, SHORT SELL, BUY TO COVER.",
        ),
    ] = None,
    value_date: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional ISO value date that the email refers to (YYYY-MM-DD).",
        ),
    ] = None,
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional reconciliation status filter: MATCHED or UNMATCHED.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(default=200, ge=1, le=2000, description="Maximum number of rows to return."),
    ] = 200,
) -> str:
    rows = reconciliation_service.list_counterparty_email_cashflows(
        vendor=vendor,
        ccy=ccy,
        action=action,
        value_date=value_date,
        status=status,
        limit=limit,
    )
    return json.dumps({"count": len(rows), "rows": rows}, default=str)


@mcp.tool(
    name="Match_Cashflows",
    title="Reconcile cash flows",
    description=MATCH_CASHFLOWS_DESCRIPTION,
    meta={
        "unique.app/icon": "link",
        "unique.app/system-prompt": MATCH_CASHFLOWS_DESCRIPTION,
    },
)
async def match_cashflows(
    email_ids: Annotated[
        list[int] | None,
        Field(
            default=None,
            description=(
                "Optional list of counterparty_email_cashflows.id values to "
                "limit the reconciliation run. When omitted, every row in "
                "UNMATCHED status is considered."
            ),
        ),
    ] = None,
) -> str:
    result: dict[str, Any] = reconciliation_service.match_cashflows(email_ids=email_ids)
    return json.dumps(result, default=str)


@mcp.tool(
    name="Save_Counterparty_Email_Cashflow",
    title="Save counterparty (email) cash flow",
    description=SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION,
    meta={
        "unique.app/icon": "mail-plus",
        "unique.app/system-prompt": SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION,
    },
)
async def save_counterparty_email_cashflow(
    amount: Annotated[
        float,
        Field(description="Signed amount as it appears on the counterparty email."),
    ],
    ccy: Annotated[
        str,
        Field(description="ISO currency code (USD, EUR, GBP, JPY, ...)."),
    ],
    vendor: Annotated[
        str,
        Field(description="Counterparty / vendor name as written in the email."),
    ],
    action: Annotated[
        str,
        Field(description="One of BUY, SELL, SHORT SELL, BUY TO COVER."),
    ],
    value_date: Annotated[
        str,
        Field(description="ISO date the email refers to (YYYY-MM-DD)."),
    ],
    email_ref: Annotated[
        str | None,
        Field(default=None, description="Optional reference to the source email."),
    ] = None,
) -> str:
    result = reconciliation_service.save_counterparty_email_cashflow(
        amount=amount,
        ccy=ccy,
        vendor=vendor,
        action=action,
        value_date=value_date,
        email_ref=email_ref,
    )
    return json.dumps(result, default=str)


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    FAVICON_PATH = Path(__file__).parent / "favicon.ico"
    return FileResponse(FAVICON_PATH)


def main():
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.getenv("MCP_PORT", "8003")),
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
