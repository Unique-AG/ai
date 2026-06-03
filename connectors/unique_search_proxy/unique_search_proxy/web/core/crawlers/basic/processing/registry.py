from __future__ import annotations

from collections.abc import Awaitable, Callable

from unique_search_proxy.web.core.crawlers.basic.processing.errors import (
    ContentProcessingError,
    ContentProcessingTimeoutError,
)
from unique_search_proxy.web.core.crawlers.basic.processing.policy import (
    ContentTypeHandlerPolicy,
)
from unique_search_proxy.web.core.crawlers.basic.processing.processors import (
    process_html,
    process_pdf,
    process_plain_text,
)

ContentProcessor = Callable[..., Awaitable[str]]

# Built-in processors keyed by exact media type. Register new types here.
CONTENT_TYPE_PROCESSORS: dict[str, ContentProcessor] = {
    "text/html": process_html,
    "application/xhtml+xml": process_html,
    "text/plain": process_plain_text,
    "text/markdown": process_plain_text,
    "application/pdf": process_pdf,
}


def normalize_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.strip().lower() or None


def resolve_handler_policy(
    content_type: str | None,
    handlers: dict[str, ContentTypeHandlerPolicy],
) -> ContentTypeHandlerPolicy | None:
    """Return the configured policy for a media type, or None when not listed."""
    normalized = normalize_content_type(content_type)
    if normalized is None:
        return None
    return handlers.get(normalized)


def resolve_processor(content_type: str | None) -> ContentProcessor | None:
    normalized = normalize_content_type(content_type)
    if normalized is None:
        return None
    return CONTENT_TYPE_PROCESSORS.get(normalized)


async def process_content(
    body: str,
    content_type: str | None,
    *,
    handlers: dict[str, ContentTypeHandlerPolicy],
    timeout: float,
) -> str | None:
    """Apply configured handlers: allow runs a processor; forbid/unlisted skips processing."""
    policy = resolve_handler_policy(content_type, handlers)
    if policy is not ContentTypeHandlerPolicy.ALLOW:
        return None

    processor = resolve_processor(content_type)
    if processor is None:
        label = normalize_content_type(content_type) or "unknown"
        raise ContentProcessingError(
            f"No processor registered for allowed content type {label}",
        )

    try:
        return await processor(body, timeout=timeout)
    except TimeoutError as exc:
        label = normalize_content_type(content_type) or "unknown"
        raise ContentProcessingTimeoutError(
            f"Processing timed out for content type {label} after {timeout}s",
        ) from exc
    except ContentProcessingError:
        raise
    except Exception as exc:
        label = normalize_content_type(content_type) or "unknown"
        raise ContentProcessingError(
            f"Processing failed for content type {label}: {exc}",
        ) from exc
