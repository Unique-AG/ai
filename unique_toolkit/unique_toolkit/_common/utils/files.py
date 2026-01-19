import mimetypes
from enum import StrEnum
from pathlib import Path


class FileMimeType(StrEnum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    PPT = "application/vnd.ms-powerpoint"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    CSV = "text/csv"
    HTML = "text/html"
    MD = "text/markdown"
    TXT = "text/plain"
    JSON = "application/json"


def get_common_name(extension: FileMimeType) -> str:
    match extension:
        case FileMimeType.DOCX | FileMimeType.DOC:
            return "docx"
        case FileMimeType.XLSX | FileMimeType.XLS:
            return "excel"
        case FileMimeType.PPT | FileMimeType.PPTX:
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
        case _:
            return "unknown"


def is_docx_mime(filepath: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type == FileMimeType.DOCX


def is_pdf_mime(filepath: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type == FileMimeType.PDF


def is_xlsx_mime(filepath: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type in [FileMimeType.XLSX, FileMimeType.XLS]


def is_pptx_mime(filepath: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type in [FileMimeType.PPTX, FileMimeType.PPT]


def is_json_mime(filepath: Path) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type == FileMimeType.JSON



def is_valid_mime(
        filepath: Path, valid_mimes: list[FileMimeType]
) -> bool:
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type in valid_mimes


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
