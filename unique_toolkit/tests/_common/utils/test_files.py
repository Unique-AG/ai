import mimetypes
from pathlib import Path

import pytest

from unique_toolkit._common.utils.files import (
    FileMimeType,
    get_common_name,
    get_file_extensions,
    guess_mime_type,
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
        (FileMimeType.MSG, "email"),
        (FileMimeType.EML, "email"),
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


def test_get_file_extensions_email_types_do_not_depend_on_registry(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Purpose: `.msg` has no entry in Python's mimetypes registry, so the
    extension must come from the toolkit's own override table.
    Why this matters: UN-24575 — downstream tools build upload filters from
    these extensions; a missing `.msg` would silently exclude Outlook mails.
    Setup summary: Force guess_extension to None; assert overrides still win.
    """
    monkeypatch.setattr(mimetypes, "guess_extension", lambda _: None)

    assert get_file_extensions([FileMimeType.MSG, FileMimeType.EML]) == [
        ".msg",
        ".eml",
    ]


# ---------------------------------------------------------------------------
# guess_mime_type — extension overrides beat the stdlib registry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("mail.msg", "application/vnd.ms-outlook"),
        ("MAIL.MSG", "application/vnd.ms-outlook"),
        ("mail.eml", "message/rfc822"),
        (Path("dir/mail.msg"), "application/vnd.ms-outlook"),
        ("report.pdf", "application/pdf"),
        ("file.unknown", None),
    ],
)
def test_guess_mime_type(filename, expected):
    assert guess_mime_type(filename) == expected


def test_guess_mime_type_msg_ignores_registry(monkeypatch: pytest.MonkeyPatch):
    """
    Purpose: Verify `.msg` classification does not depend on the host's
    `/etc/mime.types` (which may be absent, or map `.msg` differently).
    Why this matters: UN-24575 — macOS returns (None, None) for `.msg` while
    some Linux images return a type; behaviour must be identical everywhere.
    Setup summary: Make the stdlib registry return a bogus type; the override
    must still win.
    """
    monkeypatch.setattr(
        mimetypes, "guess_type", lambda *_a, **_k: ("application/x-bogus", None)
    )

    assert guess_mime_type("mail.msg") == "application/vnd.ms-outlook"
    assert is_file_content("mail.msg") is True


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("file.pdf", True),
        ("file.docx", True),
        ("file.json", True),
        ("file.txt", True),
        ("mail.msg", True),
        ("mail.MSG", True),
        ("mail.eml", True),
        ("image.png", False),
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
        ("mail.msg", False),
        ("mail.eml", False),
    ],
)
def test_is_image_content(filename, expected):
    assert is_image_content(filename) is expected


def test_is_image_content_unknown_extension():
    assert is_image_content("file.unknown") is False


# ---------------------------------------------------------------------------
# FileMimeType.from_mime_string
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mime,expected",
    [
        ("application/pdf", FileMimeType.PDF),
        ("text/csv", FileMimeType.CSV),
        (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            FileMimeType.XLSX,
        ),
        ("application/vnd.ms-excel", FileMimeType.XLS),
        ("application/vnd.ms-outlook", FileMimeType.MSG),
        ("message/rfc822", FileMimeType.EML),
    ],
)
def test_from_mime_string_known(mime, expected):
    assert FileMimeType.from_mime_string(mime) == expected


def test_from_mime_string_unknown():
    assert FileMimeType.from_mime_string("application/x-unknown-type") is None


def test_from_mime_string_empty():
    assert FileMimeType.from_mime_string("") is None


# ---------------------------------------------------------------------------
# FileMimeType instance properties
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mime,prop,expected",
    [
        (FileMimeType.DOCX, "is_docx", True),
        (FileMimeType.DOC, "is_docx", True),
        (FileMimeType.PDF, "is_docx", False),
        (FileMimeType.PDF, "is_pdf", True),
        (FileMimeType.DOCX, "is_pdf", False),
        (FileMimeType.XLSX, "is_xlsx", True),
        (FileMimeType.XLS, "is_xlsx", True),
        (FileMimeType.MSEXCEL, "is_xlsx", True),
        (FileMimeType.EXCEL, "is_xlsx", True),
        (FileMimeType.PDF, "is_xlsx", False),
        (FileMimeType.PPTX, "is_pptx", True),
        (FileMimeType.PPT, "is_pptx", True),
        (FileMimeType.MSPPT, "is_pptx", True),
        (FileMimeType.PDF, "is_pptx", False),
        (FileMimeType.JSON, "is_json", True),
        (FileMimeType.PDF, "is_json", False),
        (FileMimeType.CSV, "is_csv", True),
        (FileMimeType.PDF, "is_csv", False),
        (FileMimeType.MSG, "is_email", True),
        (FileMimeType.EML, "is_email", True),
        (FileMimeType.PDF, "is_email", False),
    ],
)
def test_mime_type_properties(mime, prop, expected):
    assert getattr(mime, prop) is expected


# ---------------------------------------------------------------------------
# is_*_mime returns False for unknown extension (None guard)
# ---------------------------------------------------------------------------


def test_is_docx_mime_unknown_extension():
    assert FileMimeType.is_docx_mime(Path("file.unknown")) is False


def test_is_pdf_mime_unknown_extension():
    assert FileMimeType.is_pdf_mime(Path("file.unknown")) is False


def test_is_xlsx_mime_unknown_extension():
    assert FileMimeType.is_xlsx_mime(Path("file.unknown")) is False


def test_is_pptx_mime_unknown_extension():
    assert FileMimeType.is_pptx_mime(Path("file.unknown")) is False


def test_is_json_mime_unknown_extension():
    assert FileMimeType.is_json_mime(Path("file.unknown")) is False
