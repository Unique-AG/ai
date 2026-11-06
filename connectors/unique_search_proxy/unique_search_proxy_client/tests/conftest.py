# Shared pytest fixtures for unique_search_proxy tests.

from __future__ import annotations

import socket
from collections.abc import Callable

import pytest
import unique_search_proxy_core.url_safety.dns as url_safety_dns


@pytest.fixture(autouse=True)
def disable_context_header_enforcement_for_legacy_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep existing TestClient integration tests working without tenant headers."""
    from unique_search_proxy_client.web.settings.app import AppSettings

    monkeypatch.setattr(
        "unique_search_proxy_client.web.middleware.context.app_settings",
        AppSettings(require_context_headers=False),
    )


@pytest.fixture(autouse=True)
def stable_public_dns_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return a deterministic public IP for dotted hostnames during unit tests."""

    def fake_getaddrinfo(host: str, *args: object, **kwargs: object) -> list[tuple]:
        normalized_host = str(host).rstrip(".").lower()
        if "." not in normalized_host:
            raise socket.gaierror("single-label host not resolved in tests")

        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443),
            )
        ]

    monkeypatch.setattr(url_safety_dns.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture(autouse=True)
def disable_url_safety_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate crawl URLs directly in tests without HTTP redirect discovery."""
    import unique_search_proxy_core.url_safety.service as service_module

    monkeypatch.setattr(
        service_module,
        "url_safety_settings",
        service_module.url_safety_settings.model_copy(
            update={"resolve_redirects": False}
        ),
    )


def _make_pdf(pages: list[str]) -> bytes:
    """Return a valid PDF with one line of Helvetica text per page."""
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Kids ["
            + " ".join(f"{4 + 2 * index} 0 R" for index in range(len(pages)))
            + f"] /Count {len(pages)} >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, text in enumerate(pages):
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {5 + 2 * index} 0 R >>"
            ).encode()
        )
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_offset = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_offset,
    )
    return bytes(out)


@pytest.fixture
def make_pdf() -> Callable[[list[str]], bytes]:
    """Build small text PDFs in tests without binary fixtures."""
    return _make_pdf


@pytest.fixture(autouse=True)
def reset_pdf_wiring() -> None:
    """Keep PDF processor singletons from leaking across tests."""
    from unique_search_proxy_client.web.core.crawlers.basic.processing.processors.pdf.wiring import (
        reset_pdf_wiring_for_tests,
    )

    reset_pdf_wiring_for_tests()
    yield
    reset_pdf_wiring_for_tests()
