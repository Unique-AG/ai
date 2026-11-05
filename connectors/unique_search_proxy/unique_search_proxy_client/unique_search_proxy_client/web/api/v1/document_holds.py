from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import Response

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.wiring import (
    get_pdf_hold_store,
)

router = APIRouter(tags=["document-holds"])


@router.get(
    "/document-holds/{document_id}",
    response_class=Response,
    summary="Download a held document",
    description=(
        "Stream and consume a pod-local document hold created when a crawled "
        "PDF exceeded the inline extraction budget. Requires "
        "``Authorization: Bearer <one-time-token>`` from the crawl handle."
    ),
)
async def download_document_hold(
    document_id: str,
    authorization: str | None = Header(default=None),
) -> Response:
    """Stream and consume a pod-local document hold."""
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    payload = get_pdf_hold_store().consume(document_id, token=token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document hold not found or expired",
        )
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{document_id}.pdf"',
        },
    )


__all__ = ["router"]
