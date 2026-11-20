"""Error handling shared by dataset MCP tools."""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, TypeVar

from fastmcp.exceptions import ToolError

R = TypeVar("R")


def tool_errors(
    logger: logging.Logger,
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Log the full traceback, then re-raise as an MCP tool error.

    Tools annotate only their domain model as a return type, so the TypeSpec
    contract stays honest: a failure travels as a protocol-level error the
    client sees via `isError`, rather than a success payload the caller has to
    sniff for an `error` key.

    Supports both sync and async tool handlers.
    """

    def decorate(func: Callable[..., R]) -> Callable[..., R]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> R:
                try:
                    return await func(*args, **kwargs)
                except ToolError:
                    raise
                except Exception as exc:
                    logger.exception("Tool %s failed", func.__name__)
                    raise ToolError(f"{type(exc).__name__}: {exc}") from exc

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            try:
                return func(*args, **kwargs)
            except ToolError:
                raise
            except Exception as exc:
                logger.exception("Tool %s failed", func.__name__)
                raise ToolError(f"{type(exc).__name__}: {exc}") from exc

        return wrapper

    return decorate
