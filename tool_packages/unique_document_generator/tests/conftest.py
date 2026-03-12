import pytest


@pytest.fixture
def sample_markdown() -> str:
    return "# Test Document\n\n## Section 1\n\nHello world.\n"


@pytest.fixture
def template_bytes() -> bytes:
    return b"PK\x03\x04fake-docx-template-bytes"
