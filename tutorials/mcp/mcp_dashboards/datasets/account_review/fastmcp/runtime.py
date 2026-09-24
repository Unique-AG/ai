"""Process-wide settings, repository, and FastMCP instance."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from unique_mcp.auth.zitadel.oidc_proxy import (
    ZitadelOIDCProxySettings,
    create_zitadel_oidc_proxy,
)
from unique_mcp.settings import ServerSettings

import paths as _paths  # noqa: F401
from constants import logger
from mcp_dashboards.settings import AppSettings
from paths import DATASET_ROOT
from repository import AccountReviewRepository


def _load_settings() -> AppSettings:
    """Dataset-local defaults, overridable by EXCEL_PATH / SQLITE_PATH / AUTH_DISABLED."""
    kwargs: dict[str, Any] = {}
    # Constructor kwargs beat env vars — only inject defaults when unset so Azure
    # can persist the DB at SQLITE_PATH=/home/data/account_review.sqlite.
    if "EXCEL_PATH" not in os.environ:
        kwargs["excel_path"] = DATASET_ROOT / "data" / "account_review_dataset.xlsx"
    if "SQLITE_PATH" not in os.environ:
        kwargs["sqlite_path"] = DATASET_ROOT / "data" / "account_review.sqlite"
    # Live-local and tests run without Zitadel. deploy.sh sets AUTH_DISABLED=false
    # when ZITADEL_* credentials are present.
    if "AUTH_DISABLED" not in os.environ:
        kwargs["auth_disabled"] = True
    return AppSettings(**kwargs)


def _build_mcp(cfg: AppSettings) -> FastMCP:
    if cfg.auth_disabled:
        logger.warning("AUTH_DISABLED=true — Zitadel OIDC is off (local demos only)")
        return FastMCP("Account Review Dashboard")

    oidc_proxy = create_zitadel_oidc_proxy(
        mcp_server_base_url=server_settings.base_url.encoded_string(),
        zitadel_oidc_proxy_settings=ZitadelOIDCProxySettings(),  # type: ignore[call-arg]
    )
    return FastMCP("Account Review Dashboard", auth=oidc_proxy)


def bind_host_and_port() -> tuple[str, int]:
    """Prefer UNIQUE_MCP_LOCAL_BASE_URL; fall back to AppSettings host/port (8004)."""
    if os.environ.get("UNIQUE_MCP_LOCAL_BASE_URL"):
        parsed = urlparse(str(server_settings.local_base_url))
        return parsed.hostname or "127.0.0.1", parsed.port or settings.port
    return settings.host, settings.port


def allowed_hosts() -> list[str]:
    """Hostnames FastMCP may accept in the Host header (public URL + bind host)."""
    hosts: list[str] = []
    for url in (server_settings.public_base_url, server_settings.local_base_url):
        if url is None:
            continue
        hostname = urlparse(str(url)).hostname
        if hostname and hostname not in hosts:
            hosts.append(hostname)
    if settings.host not in hosts and settings.host not in {"0.0.0.0", "127.0.0.1"}:
        hosts.append(settings.host)
    return hosts


settings = _load_settings()
server_settings = ServerSettings()
repo = AccountReviewRepository(settings=settings)
mcp = _build_mcp(settings)

# CORS for browser clients (live-local dashboard). Streamable HTTP returns the
# session id as a response header that the client must echo — expose it.
custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
]
