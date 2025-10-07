import mimetypes
from enum import StrEnum


class FileMimeType(StrEnum):
    PDF = "application/pdf"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOC = "application/msword"
    XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    XLS = "application/vnd.ms-excel"
    PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    CSV = "text/csv"
    HTML = "text/html"
    MD = "text/markdown"
    TXT = "text/plain"


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
