"""OpenAPI documentation for tenant context headers enforced by middleware."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header
from unique_search_proxy_core.context import (
    CHAT_ID_HEADER,
    COMPANY_ID_HEADER,
    LOCAL_REQUEST_CONTEXT,
    USER_ID_HEADER,
)


async def document_request_context_headers(
    x_unique_company_id: Annotated[
        str,
        Header(
            alias=COMPANY_ID_HEADER,
            description="Tenant company identifier.",
        ),
    ] = LOCAL_REQUEST_CONTEXT.company_id,
    x_unique_user_id: Annotated[
        str,
        Header(
            alias=USER_ID_HEADER,
            description="Tenant user identifier.",
        ),
    ] = LOCAL_REQUEST_CONTEXT.user_id,
    x_unique_chat_id: Annotated[
        str,
        Header(
            alias=CHAT_ID_HEADER,
            description="Tenant chat or session identifier.",
        ),
    ] = LOCAL_REQUEST_CONTEXT.chat_id,
) -> None:
    """Declare context headers on /v1 routes for Swagger; enforcement is in middleware."""
    return None


__all__ = ["document_request_context_headers"]
