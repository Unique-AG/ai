"""Shared settings helpers and package-level exports."""

from unique_search_proxy_client.web.settings.base import (
    get_env_path,
    is_test_runtime,
    settings_config,
)

__all__ = ["get_env_path", "is_test_runtime", "settings_config"]
