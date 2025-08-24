import base64
import gzip
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.tools.config import get_configuration_dict
from unique_toolkit.tools.utils.source_handling.schema import SourceFormatConfig


# TODO: this needs to be more general as the tools can potentially return anything maybe make a base class and then derive per "type" of tool
class ToolCallResponse(BaseModel):
    id: str
    name: str
    debug_info: Optional[dict] = None  # TODO: Make the default {}
    content_chunks: Optional[list[ContentChunk]] = None  # TODO: Make the default []
    reasoning_result: Optional[dict] = None  # TODO: Make the default {}
    error_message: str = ""

    @property
    def successful(self) -> bool:
        return self.error_message == ""


class BaseToolConfig(BaseModel):
    model_config = get_configuration_dict()
    # TODO: add a check for the parameters to all be consistent within the tool config
    pass


class Source(BaseModel):
    """Represents the sources in the tool call response that the llm will see

    Args:
        source_number: The number of the source
        content: The content of the source
    """

    model_config = ConfigDict(
        validate_by_alias=True, serialize_by_alias=True, validate_by_name=True
    )

    source_number: int | None = Field(
        default=None,
        serialization_alias="[source_number] - Used for citations!",
        validation_alias="[source_number] - Used for citations!",
    )
    content: str = Field(
        serialization_alias="[content] - Content of source",
        validation_alias="[content] - Content of source",
    )
    order: int = Field(
        serialization_alias="[order] - Index in the document!",
        validation_alias="[order] - Index in the document!",
    )
    chunk_id: str | None = Field(
        default=None,
        serialization_alias="[chunk_id] - IGNORE",
        validation_alias="[chunk_id] - IGNORE",
    )
    id: str = Field(
        serialization_alias="[id] - IGNORE",
        validation_alias="[id] - IGNORE",
    )
    key: str | None = Field(
        default=None,
        serialization_alias="[key] - IGNORE",
        validation_alias="[key] - IGNORE",
    )
    metadata: dict[str, str] | str | None = Field(
        default=None,
        serialization_alias="[metadata] - Formatted metadata",
        validation_alias="[metadata] - Formatted metadata",
    )
    url: str | None = Field(
        default=None,
        serialization_alias="[url] - IGNORE",
        validation_alias="[url] - IGNORE",
    )

    @field_validator("metadata", mode="before")
    def _metadata_str_to_dict(
        cls, v: str | dict[str, str] | None
    ) -> dict[str, str] | None:
        """
        Accept   • dict   → keep as-is
                 • str    → parse tag-string back to dict
        """
        if v is None or isinstance(v, dict):
            return v

        # v is the rendered string.  Build a dict by matching the
        # patterns defined in SourceFormatConfig.sections.
        cfg = SourceFormatConfig()  # or inject your app-wide config
        out: dict[str, str] = {}
        for key, tmpl in cfg.sections.items():
            pattern = cfg.template_to_pattern(tmpl)
            m = re.search(pattern, v, flags=re.S)
            if m:
                out[key] = m.group(1).strip()

        return out if out else v  # type: ignore

    # Compression + Base64 for url to hide it from the LLM
    @field_serializer("url")
    def serialize_url(self, value: str | None) -> str | None:
        if value is None:
            return None
        # Compress then base64 encode
        compressed = gzip.compress(value.encode())
        return base64.b64encode(compressed).decode()

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value: Any) -> str | None:
        if value is None or isinstance(value, str) and not value:
            return None
        if isinstance(value, str):
            try:
                # Try to decode base64 then decompress
                decoded_bytes = base64.b64decode(value.encode())
                decompressed = gzip.decompress(decoded_bytes).decode()
                return decompressed
            except Exception:
                # If decoding/decompression fails, assume it's plain text
                return value
        return str(value)


class ToolPrompts(BaseModel):
    name: str
    display_name: str
    tool_description: str
    tool_format_information_for_system_prompt: str
    input_model: dict[str, Any]
