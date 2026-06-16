from __future__ import annotations

from unique_search_proxy_client.web.core.agent_engines import (
    register_builtin_agent_engines,
)
from unique_search_proxy_client.web.core.crawlers import register_builtin_crawlers
from unique_search_proxy_client.web.core.search_engines import (
    register_builtin_search_engines,
)


def register_builtin_providers() -> None:
    """Register built-in search engines, agent engines, and crawlers."""
    register_builtin_search_engines()
    register_builtin_agent_engines()
    register_builtin_crawlers()
