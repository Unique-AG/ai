"""mcp_crm.py — the RM Agent "CRM" MCP server.

The CRM server is the relationship side of the RM Agent: who we serve and the
context around them. Each domain lives in its own module and is wired in with a
single ``register(mcp)`` call.

Domains
-------
  ✅ crm            — party identity / identifiers / relationship / mandate / history /
                      entity ownership + client roster + document catalogue
  ✅ client_memory  — editable talking points / open questions / pinned documents (stateful)
  ✅ calendar       — meetings (get_meetings / get_next_meeting)

Built the same way as ``mcp_sql_demo`` / ``mcp_advisory``: a standalone FastMCP HTTP
server backed by PostgreSQL (data seeded from ``sql/*.sql``, read with psycopg2),
deployed to an Azure Web App. Shares the same database as the Advisory server.

Run locally:   uv run python src/mcp_crm/mcp_crm.py
MCP endpoint:  http://127.0.0.1:8004/mcp   (point an MCP client / Unique connector here)

OAuth (Zitadel) is wired the same way as mcp_sql_demo but is OPTIONAL: when the
upstream OAuth env vars are absent the server runs open.
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

import client_memory
import crm
import dashboard
import meetings
import person_lookup
from common.db import RESET_DEMO_DATA_DESCRIPTION, reset_demo_data
from common.env_map import KNOWN_ENVS, set_url_env
from common.oauth_metadata import AdvertisePostAuthOnly
from common.tool_prompts import tool_meta

load_dotenv()

PORT = int(os.getenv("PORT", "8004"))


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
    upstream OAuth env vars are present. Returns ``None`` (open server) otherwise."""
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
            "mcp:tools", "mcp:prompts", "mcp:resources", "mcp:resource-templates",
            "email", "openid", "profile",
        ],
        forward_pkce=True,
        token_endpoint_auth_method="client_secret_post",
        extra_authorize_params=None,
        extra_token_params=None,
        client_storage=PostgreSQLStore(url=_pg_client_storage_url()),
    )


class EnvPathMiddleware:
    """Make the connector URL carry the environment in its PATH — ``…/<env>/mcp``.

    The RM Agent MCPs are one shared deployment across environments, and KB content ids
    are env-specific (see ``common.env_map``). The env signal has to ride on the connector
    URL, which is the only thing settable per environment in admin. The admin rejects a
    ``?env=`` query string but accepts a plain path, so we encode the env as a path segment.

    This pure-ASGI middleware runs before FastMCP's router: if a path segment matches a
    known env (``/sales/mcp`` or ``/mcp/sales``) it records it (``set_url_env``) for the
    resolver and rewrites the path so the endpoint still routes as ``/mcp``. Requests with
    no env segment are passed through untouched (→ ``DEFAULT_ENV``)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            segments = [s for s in scope.get("path", "").split("/") if s]
            env = next((s for s in segments if s in KNOWN_ENVS), "")
            set_url_env(env)
            if env:
                new_path = "/" + "/".join(s for s in segments if s != env)
                # Carry the env two ways: the ContextVar (fast path) AND on the request
                # scope, which travels with the Request that get_http_request() returns —
                # so the resolver still finds it even if the tool runs in a task that only
                # re-establishes FastMCP's own request context.
                scope = dict(
                    scope, path=new_path, raw_path=new_path.encode("utf-8"), rm_env=env
                )
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

mcp = FastMCP("RM Agent - CRM", auth=build_auth())

# --- domains -------------------------------------------------------------------
crm.register(mcp)
client_memory.register(mcp)
meetings.register(mcp)
dashboard.register(mcp)
person_lookup.register(mcp)

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
    return JSONResponse({"server": "running", "name": "RM Agent - CRM"})


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
