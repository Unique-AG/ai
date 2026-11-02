from __future__ import annotations

from pathlib import Path
from typing import Protocol

from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.types import (
    ScanResult,
    ScanVerdict,
)


class DocumentScanner(Protocol):
    """Scan an admitted PDF for known malware before extraction."""

    @property
    def name(self) -> str: ...

    async def scan(self, path: Path, *, timeout: float) -> ScanResult: ...


class UnconfiguredDocumentScanner:
    """Default scanner: reports unavailable until a provider is wired."""

    @property
    def name(self) -> str:
        return "unconfigured"

    async def scan(self, path: Path, *, timeout: float) -> ScanResult:
        del path, timeout
        return ScanResult(
            verdict=ScanVerdict.UNAVAILABLE,
            reason="Document scanner is not configured",
            scanner_name=self.name,
        )


class FakeDocumentScanner:
    """Test double that returns a fixed verdict."""

    def __init__(
        self,
        *,
        verdict: ScanVerdict = ScanVerdict.CLEAN,
        reason: str | None = None,
        name: str = "fake",
    ) -> None:
        self._verdict = verdict
        self._reason = reason
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def scan(self, path: Path, *, timeout: float) -> ScanResult:
        del path, timeout
        return ScanResult(
            verdict=self._verdict,
            reason=self._reason,
            scanner_name=self.name,
        )


__all__ = [
    "DocumentScanner",
    "FakeDocumentScanner",
    "UnconfiguredDocumentScanner",
]
