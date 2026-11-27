"""Code interpreter types used by the generated-files postprocessor."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

CodeInterpreterFileType = Literal["image", "document", "html"]


@dataclass(frozen=True)
class CodeInterpreterContainerFile:
    """Provider-independent identity of a file in a code interpreter container."""

    container_id: str
    file_id: str
    filename: str


class CodeInterpreterFile(BaseModel):
    """A single file produced by a code interpreter execution."""

    filename: str
    content_id: str
    type: CodeInterpreterFileType


class CodeInterpreterBlock(BaseModel):
    """A code interpreter execution paired with the files it produced."""

    code: str
    files: list[CodeInterpreterFile]
