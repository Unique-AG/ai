"""mcp_advisory.py — the RM Agent "Advisory" MCP server.

The Advisory server is the investment/portfolio side of the RM Agent: the market
intelligence and portfolio data the RM uses to advise. Each domain lives in its
own subpackage and is wired in with a single ``register(mcp)`` call (adding a new
domain is a one-line ``register()``).

Domains
-------
  ✅ house_views      — CIO house view / themes / tactical calls
  ✅ portfolios       — holdings / performance / transactions / attribution / risk
  ✅ transactions     — corporate actions / elections / orders / tax lots / monitoring
  ✅ model_portfolios — catalogue (list/get) / recommendation
  ✅ lombard          — facility coverage scenarios

Built the same way as ``mcp_sql_demo``: a standalone FastMCP HTTP server backed
by PostgreSQL (data seeded from ``sql/*.sql``, read with psycopg2), deployed to
an Azure Web App. The relationship side (CRM, client memory, calendar) is a
separate server, ``mcp_crm``.

Run locally:   uv run python src/mcp_advisory/mcp_advisory.py
MCP endpoint:  http://127.0.0.1:8003/mcp   (point an MCP client / Unique connector here)

OAuth (Zitadel) is wired the same way as mcp_sql_demo but is OPTIONAL: when the
upstream OAuth env vars are absent the server runs open, so local/demo use needs
no auth infrastructure. Set them (see README) to enable the same auth in prod.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

import house_views
import lombard
import model_portfolios
import portfolios
import transactions
from common.db import RESET_DEMO_DATA_DESCRIPTION, reset_demo_data
from common.oauth_metadata import AdvertisePostAuthOnly
from common.tool_prompts import tool_meta

load_dotenv()

PORT = int(os.getenv("PORT", "8003"))


def _pg_client_storage_url() -> str:
    url = os.getenv("PG_CLIENT_STORAGE_URL")
    if url:
        return url
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "postgres")
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "mcpdb")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def build_auth():
    """Build the same Zitadel OAuth proxy as mcp_sql_demo — but only when the
    upstream OAuth env vars are present. Returns ``None`` (open server) otherwise
    so the demo runs without auth infrastructure."""
    upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID")
    upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET")
    zitadel_url = os.getenv("ZITADEL_URL")
    if not (upstream_client_id and upstream_client_secret and zitadel_url):
        return None

    from fastmcp.server.auth.oauth_proxy import OAuthProxy
    from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier
    from key_value.aio.stores.postgresql import PostgreSQLStore

    base_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "BASE_URL_ENV", f"http://localhost:{PORT}"
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
        valid_scopes=[
            "mcp:tools",
            "mcp:prompts",
            "mcp:resources",
            "mcp:resource-templates",
            "email",
            "openid",
            "profile",
        ],
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
        client_storage=PostgreSQLStore(url=_pg_client_storage_url()),
    )


def _load_known_envs() -> frozenset[str]:
    """The env labels the connector URL may carry — the standard set, plus any added via
    RM_COMPANY_ENV_JSON (parity with mcp_crm.common.env_map, without depending on it)."""
    envs = {"qa", "uat", "bnpp", "sales", "local"}
    try:
        envs |= set(json.loads(os.getenv("RM_COMPANY_ENV_JSON", "") or "{}").values())
    except Exception:
        pass
    return frozenset(envs)


_KNOWN_ENVS = _load_known_envs()


class EnvPathMiddleware:
    """Accept the SAME env-in-path URL shape as the CRM server — ``…/<env>/mcp``.

    The RM Agent MCPs are one shared deployment across environments. CRM encodes the
    caller's env in the connector URL path so it can return env-specific KB content ids
    (see ``mcp_crm``). Advisory has NO env-specific data, so it resolves no env — but it
    accepts the identical URL shape so both connectors follow one rule (``…/<env>/mcp``)
    and an env-prefixed Advisory URL never 404s. The env segment is simply stripped and
    ignored, and the path rewritten to ``/mcp`` so FastMCP routes normally. Robust to
    ``/<env>/mcp`` and ``/mcp/<env>``; a path with no env segment passes through."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            segments = [s for s in scope.get("path", "").split("/") if s]
            env = next((s for s in segments if s in _KNOWN_ENVS), "")
            if env:
                new_path = "/" + "/".join(s for s in segments if s != env)
                scope = dict(scope, path=new_path, raw_path=new_path.encode("utf-8"))
        await self.app(scope, receive, send)


custom_middleware = [
    Middleware(EnvPathMiddleware),
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(AdvertisePostAuthOnly),
]

mcp = FastMCP("RM Agent - Advisory", auth=build_auth())

# --- domains -------------------------------------------------------------------
house_views.register(mcp)
portfolios.register(mcp)
transactions.register(mcp)
model_portfolios.register(mcp)
lombard.register(mcp)

# --- demo reset ----------------------------------------------------------------
_SQL_DIR = str(Path(__file__).parent / "sql")


@mcp.tool(
    name="Reset_Demo_Data",
    title="Reset demo data",
    description=RESET_DEMO_DATA_DESCRIPTION,
    meta=tool_meta("Reset_Demo_Data", {"unique.app/icon": "rotate-ccw"}),
)
def reset_demo_data_tool() -> str:
    return json.dumps(reset_demo_data(_SQL_DIR))


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running", "name": "RM Agent - Advisory"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    return FileResponse(Path(__file__).parent / "favicon.ico")


def main():
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=PORT,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
