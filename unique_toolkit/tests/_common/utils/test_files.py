import mimetypes
from pathlib import Path

import pytest

from unique_toolkit._common.utils.files import (
    FileMimeType,
    get_common_name,
    get_file_extensions,
    is_file_content,
    is_image_content,
)


@pytest.mark.parametrize(
    "mime,expected",
    [
        (FileMimeType.DOCX, "docx"),
        (FileMimeType.DOC, "docx"),
        (FileMimeType.XLSX, "excel"),
        (FileMimeType.XLS, "excel"),
        (FileMimeType.PPTX, "powerpoint"),
        (FileMimeType.PPT, "powerpoint"),
        (FileMimeType.PDF, "pdf"),
        (FileMimeType.JSON, "json"),
        (FileMimeType.CSV, "csv"),
        (FileMimeType.TXT, "text"),
        (FileMimeType.MD, "markdown"),
        (FileMimeType.HTML, "html"),
    ],
)
def test_get_common_name_known_types(mime, expected):
    assert get_common_name(mime) == expected


def test_get_common_name_unknown():
    class FakeMime(str):
        pass

    assert get_common_name(FakeMime("application/unknown")) == "unknown"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.docx", True),
        ("file.doc", True),
        ("file.pdf", False),
        ("file.txt", False),
    ],
)
def test_is_docx_mime(filename, expected):
    assert FileMimeType.is_docx_mime(Path(filename)) is expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.pdf", True),
        ("file.docx", False),
    ],
)
def test_is_pdf_mime(filename, expected):
    assert FileMimeType.is_pdf_mime(Path(filename)) is expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.xlsx", True),
        ("file.xls", True),
        ("file.csv", False),
    ],
)
def test_is_xlsx_mime(filename, expected):
    assert FileMimeType.is_xlsx_mime(Path(filename)) is expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.pptx", True),
        ("file.ppt", True),
        ("file.pdf", False),
    ],
)
def test_is_pptx_mime(filename, expected):
    assert FileMimeType.is_pptx_mime(Path(filename)) is expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.json", True),
        ("file.txt", False),
    ],
)
def test_is_json_mime(filename, expected):
    assert FileMimeType.is_json_mime(Path(filename)) is expected


def test_is_valid_mime_single_match():
    assert FileMimeType.is_valid_mime(
        Path("file.pdf"),
        valid_mimes=[FileMimeType.PDF],
    )


def test_is_valid_mime_multiple_match():
    assert FileMimeType.is_valid_mime(
        Path("file.xlsx"),
        valid_mimes=[FileMimeType.XLSX, FileMimeType.XLS],
    )


def test_is_valid_mime_no_match():
    assert not FileMimeType.is_valid_mime(
        Path("file.txt"),
        valid_mimes=[FileMimeType.PDF, FileMimeType.JSON],
    )


def test_get_file_extensions():
    extensions = get_file_extensions(
        [
            FileMimeType.PDF,
            FileMimeType.JSON,
            FileMimeType.DOCX,
        ]
    )

    assert ".pdf" in extensions
    assert ".json" in extensions
    assert ".docx" in extensions


def test_get_file_extensions_filters_none(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mimetypes, "guess_extension", lambda _: None)

    assert get_file_extensions([FileMimeType.PDF]) == []


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.pdf", True),
        ("file.docx", True),
        ("file.json", True),
        ("file.exe", False),
        ("file.unknown", False),
    ],
)
def test_is_file_content(filename, expected):
    assert is_file_content(filename) is expected


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("image.jpg", True),
        ("image.png", True),
        ("image.webp", True),
        ("file.pdf", False),
        ("file.txt", False),
    ],
)
def test_is_image_content(filename, expected):
    assert is_image_content(filename) is expected


def test_is_image_content_unknown_extension():
    assert is_image_content("file.unknown") is False
