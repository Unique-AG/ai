"""Miscellaneous lightweight resource managers."""

from typing import Any

from unique_sdk.api_resources._acronyms import Acronyms
from unique_sdk.api_resources._llm_models import LLMModels
from unique_sdk.api_resources._mcp import MCP

from .._base import BaseManager, DomainObject


# ---------------------------------------------------------------------------
# LLM Models
# ---------------------------------------------------------------------------


class ModelsManager(BaseManager):
    """List available LLM models."""

    async def list(self, **params: Any) -> Any:
        return await LLMModels.get_models_async(
            self._user_id, self._company_id, **params
        )


# ---------------------------------------------------------------------------
# Acronyms
# ---------------------------------------------------------------------------


class AcronymsObject(DomainObject):
    """Company-specific acronyms."""


class AcronymsManager(BaseManager):
    """Retrieve company acronyms."""

    async def get(self) -> AcronymsObject:
        result = await Acronyms.get_async(self._user_id, self._company_id)
        return AcronymsObject(self._user_id, self._company_id, result)


# ---------------------------------------------------------------------------
# MCP (Model Context Protocol)
# ---------------------------------------------------------------------------


class MCPResult(DomainObject):
    """Result of an MCP tool call."""


class MCPManager(BaseManager):
    """Call tools registered via the Model Context Protocol."""

    async def call_tool(self, **params: Any) -> MCPResult:
        result = await MCP.call_tool_async(self._user_id, self._company_id, **params)
        return MCPResult(self._user_id, self._company_id, result)
