from __future__ import annotations

import mimetypes
from enum import StrEnum
from pathlib import Path


class FileMimeType(StrEnum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    # TODO: clean up duplicates and make the monolith compatible with this.
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    MSEXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    EXCEL = "application/vnd.ms-excel"
    PPT = "application/vnd.ms-powerpoint"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    MSPPT = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    CSV = "text/csv"
    HTML = "text/html"
    MD = "text/markdown"
    TXT = "text/plain"
    JSON = "application/json"

    @classmethod
    def get_mime_from_file_path(cls, filepath: Path) -> "FileMimeType | None":
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type is None:
            return None

        return cls.from_mime_string(mime_type)

    @classmethod
    def from_mime_string(cls, mime: str) -> "FileMimeType | None":
        try:
            return cls(mime)
        except ValueError:
            return None

    @property
    def is_docx(self) -> bool:
        cls = self.__class__
        return self in {cls.DOCX, cls.DOC}

    @property
    def is_pdf(self) -> bool:
        return self == self.__class__.PDF

    @property
    def is_xlsx(self) -> bool:
        cls = self.__class__
        return self in {cls.XLSX, cls.XLS, cls.MSEXCEL, cls.EXCEL}

    @property
    def is_pptx(self) -> bool:
        cls = self.__class__
        return self in {cls.PPTX, cls.PPT, cls.MSPPT}

    @property
    def is_json(self) -> bool:
        return self == self.__class__.JSON

    @property
    def is_csv(self) -> bool:
        return self == self.__class__.CSV

    @classmethod
    def is_docx_mime(cls, filepath: Path) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type is not None and mime_type.is_docx

    @classmethod
    def is_pdf_mime(cls, filepath: Path) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type is not None and mime_type.is_pdf

    @classmethod
    def is_xlsx_mime(cls, filepath: Path) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type is not None and mime_type.is_xlsx

    @classmethod
    def is_pptx_mime(cls, filepath: Path) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type is not None and mime_type.is_pptx

    @classmethod
    def is_json_mime(cls, filepath: Path) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type is not None and mime_type.is_json

    @classmethod
    def is_valid_mime(cls, filepath: Path, valid_mimes: list[FileMimeType]) -> bool:
        mime_type = cls.get_mime_from_file_path(filepath)
        return mime_type in valid_mimes


def get_common_name(extension: FileMimeType) -> str:
    match extension:
        case FileMimeType.DOCX | FileMimeType.DOC:
            return "docx"
        case (
            FileMimeType.XLSX
            | FileMimeType.XLS
            | FileMimeType.MSEXCEL
            | FileMimeType.EXCEL
        ):
            return "excel"
        case FileMimeType.PPT | FileMimeType.PPTX | FileMimeType.MSPPT:
            return "powerpoint"
        case FileMimeType.PDF:
            return "pdf"
        case FileMimeType.JSON:
            return "json"
        case FileMimeType.CSV:
            return "csv"
        case FileMimeType.TXT:
            return "text"
        case FileMimeType.MD:
            return "markdown"
        case FileMimeType.HTML:
            return "html"
        case _:  # pyright: ignore[reportUnnecessaryComparison]
            return "unknown"  # pyright: ignore[reportUnreachable]


def get_file_extensions(mimes: list[FileMimeType]) -> list[str]:
    types = [mimetypes.guess_extension(mime) for mime in mimes]
    return [t for t in types if t]


class ImageMimeType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    BMP = "image/bmp"
    WEBP = "image/webp"
    TIFF = "image/tiff"
    SVG = "image/svg+xml"


def is_file_content(filename: str) -> bool:
    mimetype, _ = mimetypes.guess_type(filename)

    if not mimetype:
        return False

    return mimetype in FileMimeType.__members__.values()


def is_image_content(filename: str) -> bool:
    mimetype, _ = mimetypes.guess_type(filename)

    if not mimetype:
        return False

    return mimetype in ImageMimeType.__members__.values()
