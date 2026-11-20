"""Reusable MCP elicitation helpers."""

from __future__ import annotations

from typing import TypeVar

from fastmcp import Context
from pydantic import BaseModel

FormT = TypeVar("FormT", bound=BaseModel)


async def elicit_confirm(ctx: Context, message: str) -> bool:
    """Return true only when the user accepts a boolean confirmation."""
    result = await ctx.elicit(message, response_type=bool)
    return result.action == "accept" and bool(result.data)


async def elicit_form(
    ctx: Context, message: str, response_type: type[FormT]
) -> FormT | None:
    """Collect a typed form via MCP elicitation, or return None on cancel."""
    result = await ctx.elicit(message, response_type=response_type)
    if result.action != "accept" or result.data is None:
        return None
    return response_type.model_validate(result.data)
