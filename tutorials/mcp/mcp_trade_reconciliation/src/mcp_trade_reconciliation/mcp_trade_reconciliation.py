import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from db_tool_reconciliation import service as reconciliation_service
from db_tool_reconciliation.prompts import (
    DERIVE_BREAK_ACTIONS_DESCRIPTION,
    GET_COUNTERPARTY_EMAIL_CASHFLOWS_DESCRIPTION,
    GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION,
    MATCH_CASHFLOWS_DESCRIPTION,
    RESET_DEMO_DATA_DESCRIPTION,
    SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION,
    tool_meta,
)

load_dotenv()

def build_auth():
    """Build the Zitadel OAuth proxy — but only when the upstream OAuth env vars
    (UPSTREAM_CLIENT_ID / UPSTREAM_CLIENT_SECRET / ZITADEL_URL) are ALL present.
    Returns ``None`` (open server) otherwise — the same pattern as the RM Agent
    MCPs (mcp_advisory / mcp_crm): fine for this read-only, synthetic demo data,
    and it spares every dashboard user a per-connector OAuth "Connect" login."""
    upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID")
    upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET")
    zitadel_url = os.getenv("ZITADEL_URL")
    if not (upstream_client_id and upstream_client_secret and zitadel_url):
        return None

    from fastmcp.server.auth.oauth_proxy import OAuthProxy
    from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
    from key_value.aio.stores.postgresql import PostgreSQLStore

    base_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "BASE_URL_ENV", "https://default.ngrok-free.app"
    )

    # Persist OAuth client registrations in Postgres so they survive restarts
    # (the default in-memory registry breaks already-connected clients on redeploy).
    pg_client_storage_url = os.getenv("PG_CLIENT_STORAGE_URL")
    if pg_client_storage_url:
        client_storage = PostgreSQLStore(url=pg_client_storage_url)
    else:
        pg_user = os.getenv("PGUSER", "postgres")
        pg_password = os.getenv("PGPASSWORD", "postgres")
        pg_host = os.getenv("PGHOST", "localhost")
        pg_port = os.getenv("PGPORT", "5432")
        pg_database = os.getenv("PGDATABASE", "reconciliationdb")
        client_storage = PostgreSQLStore(
            url=f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        )

    token_verifier = IntrospectionTokenVerifier(
        introspection_url=f"{zitadel_url}/oauth/v2/introspect",
        client_id=upstream_client_id,
        client_secret=upstream_client_secret,
        client_auth_method="client_secret_basic",
    )
    return OAuthProxy(
        upstream_authorization_endpoint=f"{zitadel_url}/oauth/v2/authorize",
        upstream_token_endpoint=f"{zitadel_url}/oauth/v2/token",
        upstream_client_id=upstream_client_id,
        upstream_client_secret=upstream_client_secret,
        upstream_revocation_endpoint=f"{zitadel_url}/oauth/v2/revoke",
        token_verifier=token_verifier,
        base_url=base_url,
        redirect_path=None,
        issuer_url=None,
        service_documentation_url=None,
        allowed_client_redirect_uris=None,
        valid_scopes=["email", "openid", "profile"],
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
        client_storage=client_storage,
    )

class AdvertisePostAuthOnly(BaseHTTPMiddleware):
    """Advertise only client_secret_post in the OAuth discovery metadata.

    FastMCP's token endpoint (as of 3.4.4) only parses client credentials from
    the request body, yet its metadata also advertises client_secret_basic.
    The MCP TypeScript SDK prefers client_secret_basic when advertised, so
    token exchanges from Unique's platform fail with 401 "Missing client_id".
    Dropping basic from the advertised methods steers the SDK to
    client_secret_post, which works.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/.well-known/"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            data = json.loads(body)
            for key in (
                "token_endpoint_auth_methods_supported",
                "revocation_endpoint_auth_methods_supported",
            ):
                if isinstance(data.get(key), list) and "client_secret_post" in data[key]:
                    data[key] = ["client_secret_post"]
            body = json.dumps(data).encode()
        except (ValueError, TypeError):
            pass
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )


custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(AdvertisePostAuthOnly),
]

mcp = FastMCP("Trade Reconciliation 🚀", auth=build_auth())


@mcp.tool(
    name="Get_Customer_Book_Cashflows",
    title="Customer (book) cash flows",
    description=GET_CUSTOMER_BOOK_CASHFLOWS_DESCRIPTION,
    meta=tool_meta("Get_Customer_Book_Cashflows", {"unique.app/icon": "database"}),
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
    meta=tool_meta("Get_Counterparty_Email_Cashflows", {"unique.app/icon": "mail"}),
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
    meta=tool_meta("Match_Cashflows", {"unique.app/icon": "link"}),
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
    name="Derive_Break_Actions",
    title="Derive break actions",
    description=DERIVE_BREAK_ACTIONS_DESCRIPTION,
    meta=tool_meta("Derive_Break_Actions", {"unique.app/icon": "sparkles"}),
)
async def derive_break_actions() -> str:
    result: dict[str, Any] = reconciliation_service.derive_break_actions()
    return json.dumps(result, default=str)


@mcp.tool(
    name="Save_Counterparty_Email_Cashflow",
    title="Save counterparty (email) cash flow",
    description=SAVE_COUNTERPARTY_EMAIL_CASHFLOW_DESCRIPTION,
    meta=tool_meta("Save_Counterparty_Email_Cashflow", {"unique.app/icon": "mail-plus"}),
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


@mcp.tool(
    name="Reset_Demo_Data",
    title="Reset demo data",
    description=RESET_DEMO_DATA_DESCRIPTION,
    meta=tool_meta("Reset_Demo_Data", {"unique.app/icon": "rotate-ccw"}),
)
async def reset_demo_data() -> str:
    result = reconciliation_service.reset_demo_data()
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
