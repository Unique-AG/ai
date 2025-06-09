"""
Configuration and client classes for Unique SDK v2.

This module provides the main client and context classes for the v2 SDK.
"""

import json
import os
import platform
from pathlib import Path
from typing import Dict, Optional, Self

from pydantic import BaseModel, ConfigDict, Field

from unique_client._version import __version__
from unique_client.protocols import RequestContextProtocol

# Unique Configuration & Context Classes
# =====================================


class ImmutableBaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class APIConfig(ImmutableBaseModel):
    """
    General API configuration settings for the Unique SDK.

    This contains API settings that are not app-specific.
    """

    api_base: str = Field("https://api.unique.ch", description="Base API URL")
    api_version: str = Field("2023-12-06", description="API version")
    log_level: Optional[str] = Field(None, description="Logging level (debug, info)")

    def with_overrides(self, **kwargs) -> "APIConfig":
        """Create a new instance with specified overrides."""
        return self.model_copy(update=kwargs)


class AppConfig(ImmutableBaseModel):
    """
    Application-specific configuration that includes authentication.

    Only an app can have an API key - this enforces that constraint.
    """

    api_key: str = Field(..., description="API key for authentication")
    app_id: str = Field(..., description="Application ID")

    def with_overrides(self, **kwargs) -> "AppConfig":
        """Create a new instance with specified overrides."""
        return self.model_copy(update=kwargs)


class AuthContext(BaseModel):
    """
    Authentication context for API requests.

    This represents the identity context for a specific request or session.
    """

    user_id: str = Field(..., description="User identifier")
    company_id: str = Field(..., description="Company identifier")


class UniqueRequestContext(RequestContextProtocol):
    """
    Complete context for making API requests.

    Combines API configuration, app configuration, and authentication context.
    This class handles all request preparation including headers, URLs, and validation.
    """

    def __init__(
        self,
        api_key: str,
        app_id: str,
        api_base: str,
        api_version: str,
        user_id: str,
        company_id: str,
    ):
        self.api_config = APIConfig(api_base=api_base, api_version=api_version)
        self.app_config = AppConfig(api_key=api_key, app_id=app_id)
        self.auth = AuthContext(user_id=user_id, company_id=company_id)

    def build_full_url(self, endpoint: str) -> str:
        """Build the complete URL for an endpoint."""
        return f"{self.api_config.api_base}{endpoint}"

    def build_headers(self, method: str) -> Dict[str, str]:
        """
        Build complete HTTP headers for API requests.

        Args:
            method: HTTP method (get, post, patch, delete)

        Returns:
            Dictionary of HTTP headers ready for use with APIRequestor
        """
        # Validate configuration first
        self._validate_config()

        # Get HTTP client name for user agent
        from unique_client.core.requestor import APIRequestor

        http_client = APIRequestor._get_http_client()
        http_client_name = getattr(http_client, "name", "unknown")

        # Build user agent info
        ua_info = {
            "bindings_version": __version__,
            "lang": "python",
            "publisher": "unique",
            "httplib": http_client_name,
        }

        # Add platform info safely
        for attr, func in [
            ("lang_version", platform.python_version),
            ("platform", platform.platform),
            ("uname", lambda: " ".join(platform.uname())),
        ]:
            try:
                ua_info[attr] = func()
            except Exception:
                ua_info[attr] = "(disabled)"

        headers = {
            "X-Unique-Client-User-Agent": json.dumps(ua_info),
            "User-Agent": f"Unique SDK/v1 PythonBindings/{__version__}",
            "Authorization": f"Bearer {self.app_config.api_key}",
            "x-user-id": self.auth.user_id,
            "x-company-id": self.auth.company_id,
            "x-api-version": self.api_config.api_version,
            "x-app-id": self.app_config.app_id,
        }

        if method.lower() in ["post", "patch"]:
            headers["Content-Type"] = "application/json"

        return headers

    def _validate_config(self):
        """Validate required configuration."""
        if not self.app_config.api_key:
            from unique_client.core.errors import AuthenticationError

            raise AuthenticationError(
                "No API key provided. Configure it using UniqueClient(api_key='...', app_id='...'). "
                "Generate API keys from the Unique web interface. "
                "See https://docs.unique.ch for details."
            )

        if not self.app_config.app_id:
            from unique_client.core.errors import AuthenticationError

            raise AuthenticationError(
                "No App ID provided. Configure it using UniqueClient(api_key='...', app_id='...'). "
                "Generate App IDs from the Unique web interface. "
                "See https://docs.unique.ch for details."
            )


# Main Client Class
# =================


def getenv_or_raise(name: str, default=None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


class UniqueClient:
    """
    Main client class that encapsulates configuration and provides a clean API.

    This follows the pattern used by modern SDKs like OpenAI, Anthropic, etc.
    """

    def __init__(
        self,
        api_key: str,
        app_id: str,
        user_id: str,
        company_id: str,
        api_base: str,
        api_version: str = "2023-12-06",
    ):
        """
        Initialize the Unique client.

        Args:
            api_key: API key for authentication (required)
            app_id: Application ID (required)
            user_id: User ID
            company_id: Company ID
            api_base: Base API URL
            api_version: API version
        """

        # Store configuration values
        self._api_key = api_key
        self._app_id = app_id
        self._api_base = api_base
        self._api_version = api_version
        self._user_id = user_id
        self._company_id = company_id

    # Knowledge Base
    @property
    def content(self):
        """Get a Content resource instance with the client's default context."""
        # Lazy import to avoid circular dependency
        from unique_client.unique_client.api_resources.content import Content

        context = UniqueRequestContext(
            api_key=self._api_key,
            app_id=self._app_id,
            api_base=self._api_base,
            api_version=self._api_version,
            user_id=self._user_id,
            company_id=self._company_id,
        )
        return Content(context)

    @property
    def search(self):
        """Get a Search resource instance with the client's default context."""
        # Lazy import to avoid circular dependency
        from unique_client.unique_client.api_resources.search import Search

        context = UniqueRequestContext(
            api_key=self._api_key,
            app_id=self._app_id,
            api_base=self._api_base,
            api_version=self._api_version,
            user_id=self._user_id,
            company_id=self._company_id,
        )
        return Search(context)

    # Chat
    @property
    def chat(self):
        """Get a Chat resource instance with the client's default context."""

        class ChatMessages:
            @property
            def messages(self):
                from unique_client.unique_client.api_resources.messages import Messages

                context = UniqueRequestContext(
                    api_key=self._api_key,
                    app_id=self._app_id,
                    api_base=self._api_base,
                    api_version=self._api_version,
                    user_id=self._user_id,
                    company_id=self._company_id,
                )
                return Messages(context)

        return ChatMessages()

    @classmethod
    def from_env(cls, env_file_path: Path | None = None) -> Self:
        """
        Create a UniqueClient from environment variables.

        Environment Variables:
            API_KEY: API key for authentication (required)
            APP_ID: Application ID (required)
            USER_ID: User ID (required)
            COMPANY_ID: Company ID (required)
            API_BASE: API base URL (optional, defaults to "https://api.unique.ch")
            API_VERSION: API version (optional, defaults to "2023-12-06")

        Returns:
            Configured UniqueClient instance

        Example:
            client = UniqueClient.from_env()
        """
        if env_file_path:
            try:
                from dotenv import load_dotenv

                load_dotenv(env_file_path)
            except ImportError:
                raise ImportError(
                    "python-dotenv is required for from_env(). Install with: pip install python-dotenv"
                )

        # Get configuration from environment variables
        api_key = getenv_or_raise("API_KEY")
        app_id = getenv_or_raise("APP_ID")
        user_id = getenv_or_raise("USER_ID")
        company_id = getenv_or_raise("COMPANY_ID")
        api_base = getenv_or_raise("API_BASE")
        api_version = getenv_or_raise("API_VERSION", "2023-12-06")

        return cls(
            api_key=api_key,
            app_id=app_id,
            user_id=user_id,
            company_id=company_id,
            api_base=api_base,
            api_version=api_version,
        )
