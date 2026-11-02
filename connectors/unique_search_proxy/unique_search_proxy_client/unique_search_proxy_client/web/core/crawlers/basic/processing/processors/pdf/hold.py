from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass

from unique_search_proxy_core.schema import PdfDocumentHandle

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    HeldPdfDocument,
)


@dataclass(frozen=True, slots=True)
class PdfHoldSettings:
    max_document_hold_bytes: int = 50 * 1024 * 1024
    max_document_hold_documents: int = 16
    document_hold_ttl_seconds: float = 120.0
    document_hold_base_url: str = "http://127.0.0.1:2349"


class PdfDocumentHoldStore:
    """Process-local in-memory hold for PDFs above the inline extraction budget."""

    def __init__(self, settings: PdfHoldSettings | None = None) -> None:
        self._settings = settings or PdfHoldSettings()
        self._documents: dict[str, HeldPdfDocument] = {}

    @property
    def settings(self) -> PdfHoldSettings:
        return self._settings

    def _purge_expired(self, *, now: float) -> None:
        expired = [
            document_id
            for document_id, held in self._documents.items()
            if held.expires_at_epoch <= now
        ]
        for document_id in expired:
            self._documents.pop(document_id, None)

    def _evict_oldest_until_fit(self, *, incoming_bytes: int) -> None:
        while self._documents and (
            len(self._documents) >= self._settings.max_document_hold_documents
            or sum(doc.byte_size for doc in self._documents.values()) + incoming_bytes
            > self._settings.max_document_hold_bytes
        ):
            oldest_id = min(
                self._documents,
                key=lambda document_id: self._documents[document_id].expires_at_epoch,
            )
            self._documents.pop(oldest_id, None)

    def hold(
        self,
        payload: bytes,
        *,
        page_count: int | None = None,
        now: float | None = None,
    ) -> tuple[PdfDocumentHandle, str]:
        """Store ``payload`` and return the public handle plus one-time token."""
        current = time.time() if now is None else now
        self._purge_expired(now=current)
        self._evict_oldest_until_fit(incoming_bytes=len(payload))

        document_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        expires_at = current + self._settings.document_hold_ttl_seconds
        self._documents[document_id] = HeldPdfDocument(
            document_id=document_id,
            token=token,
            expires_at_epoch=expires_at,
            byte_size=len(payload),
            page_count=page_count,
            payload=payload,
        )
        download_url = (
            f"{self._settings.document_hold_base_url.rstrip('/')}"
            f"/v1/document-holds/{document_id}"
        )
        handle = PdfDocumentHandle(
            document_id=document_id,
            download_url=download_url,
            token=token,
            expires_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expires_at)),
            byte_size=len(payload),
            page_count=page_count,
        )
        return handle, token

    def consume(
        self,
        document_id: str,
        *,
        token: str,
        now: float | None = None,
    ) -> bytes | None:
        """Return and delete the held bytes when the token matches and is fresh."""
        current = time.time() if now is None else now
        self._purge_expired(now=current)
        held = self._documents.get(document_id)
        if held is None:
            return None
        if held.expires_at_epoch <= current:
            self._documents.pop(document_id, None)
            return None
        if not secrets.compare_digest(held.token, token):
            return None
        self._documents.pop(document_id, None)
        return held.payload

    def peek(self, document_id: str) -> HeldPdfDocument | None:
        self._purge_expired(now=time.time())
        return self._documents.get(document_id)


__all__ = ["PdfDocumentHoldStore", "PdfHoldSettings"]
