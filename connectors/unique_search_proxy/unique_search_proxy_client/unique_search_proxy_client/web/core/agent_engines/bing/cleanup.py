from __future__ import annotations

import logging

from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from unique_search_proxy_core.errors import EngineNotConfiguredError

from unique_search_proxy_client.web.core.agent_engines.bing.client import (
    get_credentials,
    get_project_client,
)
from unique_search_proxy_client.web.core.agent_engines.bing.runner import (
    BING_AUTO_AGENT_NAME_PREFIX,
)
from unique_search_proxy_client.web.settings.providers.bing_agent import (
    bing_agent_credentials,
)
from unique_search_proxy_client.web.settings.secret_str import read_secret

_LOGGER = logging.getLogger(__name__)
_LIST_PAGE_SIZE = 100


def _is_auto_provisioned_agent_name(name: str) -> bool:
    return name.startswith(f"{BING_AUTO_AGENT_NAME_PREFIX}-")


async def cleanup_auto_provisioned_bing_agents(project_client: AIProjectClient) -> int:
    """Delete Foundry agents whose names match the auto-provisioned hash prefix.

    Best-effort and race-tolerant: continues on per-agent failures (including
    concurrent deletes from other workers/replicas). Treats not-found as success
    (idempotent). Returns the number of successfully deleted agents.
    """
    deleted = 0
    pager = project_client.agents.list(kind="prompt", limit=_LIST_PAGE_SIZE)
    async for agent in pager:
        name = getattr(agent, "name", None) or ""
        if not _is_auto_provisioned_agent_name(name):
            continue
        try:
            await project_client.agents.delete(name)
            deleted += 1
            _LOGGER.info("Deleted auto-provisioned Bing agent %s", name)
        except ResourceNotFoundError:
            _LOGGER.info(
                "Auto-provisioned Bing agent %s already absent during cleanup",
                name,
            )
        except Exception:
            _LOGGER.warning(
                "Failed to delete auto-provisioned Bing agent %s",
                name,
                exc_info=True,
            )
    return deleted


async def maybe_cleanup_auto_provisioned_bing_agents_on_start() -> None:
    """Best-effort startup cleanup when ``BING_AGENT_CLEANUP_ON_START`` is enabled.

    Never raises: credential, client, list, or delete failures are logged and
    swallowed so multi-worker/replica races cannot block process startup.
    Transient Bing request failures during a race are recovered by create-on-miss.
    """
    if not bing_agent_credentials.cleanup_on_start:
        return

    try:
        bing_agent_credentials.check_credentials()
    except EngineNotConfiguredError as exc:
        _LOGGER.info(
            "Skipping Bing agent startup cleanup; credentials not configured: %s",
            exc,
        )
        return

    try:
        async with get_credentials() as credential:
            async with get_project_client(
                credential,
                endpoint=read_secret(bing_agent_credentials.endpoint),
            ) as project_client:
                deleted = await cleanup_auto_provisioned_bing_agents(project_client)
        _LOGGER.info(
            "Bing agent startup cleanup finished; deleted %s auto-provisioned agent(s)",
            deleted,
        )
    except Exception:
        _LOGGER.warning("Bing agent startup cleanup failed", exc_info=True)
