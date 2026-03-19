"""Configuration from environment variables, wired into unique_sdk globals."""

from __future__ import annotations

import os
import sys

import unique_sdk


class Config:
    """Holds resolved configuration values for the CLI session."""

    user_id: str
    company_id: str
    api_key: str
    app_id: str
    api_base: str

    def __init__(
        self,
        *,
        user_id: str,
        company_id: str,
        api_key: str,
        app_id: str,
        api_base: str,
    ) -> None:
        self.user_id = user_id
        self.company_id = company_id
        self.api_key = api_key
        self.app_id = app_id
        self.api_base = api_base


def load_config() -> Config:
    """Load configuration from environment variables and wire into unique_sdk.

    Required env vars: UNIQUE_API_KEY, UNIQUE_APP_ID, UNIQUE_USER_ID, UNIQUE_COMPANY_ID.
    Optional: UNIQUE_API_BASE (defaults to the SDK default).
    """
    missing: list[str] = []
    for var in ("UNIQUE_API_KEY", "UNIQUE_APP_ID", "UNIQUE_USER_ID", "UNIQUE_COMPANY_ID"):
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print(f"Error: missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ["UNIQUE_API_KEY"]
    app_id = os.environ["UNIQUE_APP_ID"]
    user_id = os.environ["UNIQUE_USER_ID"]
    company_id = os.environ["UNIQUE_COMPANY_ID"]
    api_base = os.environ.get("UNIQUE_API_BASE", unique_sdk.api_base)

    unique_sdk.api_key = api_key
    unique_sdk.app_id = app_id
    unique_sdk.api_base = api_base

    return Config(
        user_id=user_id,
        company_id=company_id,
        api_key=api_key,
        app_id=app_id,
        api_base=api_base,
    )
