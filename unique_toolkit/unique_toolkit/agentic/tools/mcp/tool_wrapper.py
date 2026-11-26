import asyncio
import base64
import json
import logging
import mimetypes
import uuid
from collections import Counter
from typing import Any

import unique_sdk
from pydantic import ValidationError
from unique_sdk.utils.mcp_citations import (
    extract_mcp_citation_items,
    find_embedded_json,
)

from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.mcp.models import MCPToolConfig
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ToolProgressReporter
from unique_toolkit.app.schemas import ChatEvent, McpServer, McpTool
from unique_toolkit.chat.schemas import MessageLog, MessageLogStatus
from unique_toolkit.chat.service import ChatService
from unique_toolkit.content.constants import ASSISTANT_GENERATED_METADATA_KEY
from unique_toolkit.content.functions import upload_content_from_bytes
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.language_model import LanguageModelService
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

logger = logging.getLogger(__name__)

REFERENCE_META_KEY = "unique.app/reference"


class MCPToolWrapper(Tool[MCPToolConfig]):
    """Wrapper class for MCP tools that implements the Tool interface"""

    def __init__(
        self,
        mcp_server: McpServer,
        mcp_tool: McpTool,
        config: MCPToolConfig,
        event: ChatEvent,
        tool_progress_reporter: ToolProgressReporter | None = None,
        *,
        chat_service: ChatService | None = None,
        language_model_service: LanguageModelService | None = None,
    ) -> None:
        self.name = mcp_tool.name
        if chat_service is not None and language_model_service is not None:
            super().__init__(
                config,
                event,
                tool_progress_reporter=tool_progress_reporter,
                chat_service=chat_service,
                language_model_service=language_model_service,
            )
        else:
            super().__init__(config, event, tool_progress_reporter)
        self._mcp_tool = mcp_tool
        self._mcp_server = mcp_server

    def tool_description(self) -> LanguageModelToolDescription:
        """Convert MCP tool schema to LanguageModelToolDescription"""
        # Create a Pydantic model from the MCP tool's input schema
        logger.info(
            "MCP tool %s schema %s", self._mcp_tool.name, self._mcp_tool.input_schema
        )

        return LanguageModelToolDescription(
            name=self.name,
            description=self._mcp_tool.description or "",
            parameters=self._mcp_tool.input_schema,
        )

    def _json_schema_to_python_type(self, schema: dict[str, Any]) -> type:
        """Convert JSON schema type to Python type"""
        json_type = schema.get("type", "string")

        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        return type_mapping.get(json_type, str)

    def tool_description_for_system_prompt(self) -> str:
        """Return tool description for system prompt"""
        # Not using jinja here to keep it simple and not import new packages.
        lines = [
            f"**MCP Server**: {self._mcp_server.name}",
            f"**Tool Name**: {self.name}",
        ]
        if self._mcp_tool.system_prompt:
            lines.append(self._mcp_tool.system_prompt)

        return "\n".join(lines)

    def tool_description_for_user_prompt(self) -> str:
        return self._mcp_tool.user_prompt or ""

    def tool_format_information_for_user_prompt(self) -> str:
        return ""

    def tool_format_information_for_system_prompt(self) -> str:
        """Return formatting information for system prompt"""
        return self._mcp_tool.tool_format_information or ""

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        """Return evaluation check list - empty for MCP tools for now"""
        # TODO: this is empty for now as it requires a setting in the backend for choosing a suitable validator.
        return []

    def get_evaluation_checks_based_on_tool_response(
        self,
        tool_response: ToolCallResponse,
    ) -> list[EvaluationMetricName]:
        """Return evaluation checks based on tool response"""
        return []

    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        active_message_log: MessageLog | None = None

        """Execute the MCP tool using SDK to call public API"""
        self.logger.info(f"Running MCP tool: {self.name}")

        # Create message log entry for the MCP tool run
        active_message_log = self._create_or_update_message_log(
            progress_message="_Executing MCP tool_",
            active_message_log=active_message_log,
        )

        try:
            # Robust argument extraction and validation
            arguments = self._extract_and_validate_arguments(tool_call)

            # Use SDK to call the public API
            result = await self._call_mcp_tool_via_sdk(arguments)

            content_chunks, references = self._extract_structured_references(result)
            remainder = None
            if not content_chunks:
                content_chunks, references, remainder = (
                    self._try_extract_record_references(result)
                )
            content_str, image_data_urls = await asyncio.to_thread(
                self._process_mcp_result, result
            )
            if content_chunks:
                # Structured references already carry the text; keep any
                # extracted images but drop the redundant flat text.
                content_str = ""

            # TODO: Why result here not applied directly to the body of the tool_response? like so how does it know the results in the history?
            tool_response = ToolCallResponse(
                id=tool_call.id or "",
                name=self.name,
                debug_info={
                    "mcp_tool": self.name,
                    "mcp_server": self._mcp_server.name,
                    "arguments": arguments,
                },
                error_message="",
                content=content_str,
                content_chunks=content_chunks or None,
                image_data_urls=image_data_urls,
                system_reminder=remainder or "",
            )

            # Update message log entry to completed
            active_message_log = self._create_or_update_message_log(
                progress_message="_Completed MCP tool_",
                status=MessageLogStatus.COMPLETED,
                active_message_log=active_message_log,
                references=references,
            )

            return tool_response

        except Exception as e:
            self.logger.error(f"Error executing MCP tool {self.name}: {e}")

            # Update message log entry to failed
            active_message_log = self._create_or_update_message_log(
                progress_message="_Failed executing MCP tool_",
                status=MessageLogStatus.FAILED,
            )

            return ToolCallResponse(
                id=tool_call.id or "",
                name=self.name,
                debug_info={
                    "mcp_tool": self.name,
                    "mcp_server": self._mcp_server.name,
                    "error": str(e),
                    "original_arguments": getattr(tool_call, "arguments", None),
                },
                error_message=str(e),
            )

    def _create_or_update_message_log(
        self,
        *,
        progress_message: str | None = None,
        status: MessageLogStatus = MessageLogStatus.RUNNING,
        active_message_log: MessageLog | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog | None:
        return self._message_step_logger.create_or_update_message_log(
            active_message_log=active_message_log,
            header=self.display_name(),
            progress_message=progress_message,
            status=status,
            references=references or [],
        )

    def _extract_and_validate_arguments(
        self, tool_call: LanguageModelFunction
    ) -> dict[str, Any]:
        """
        Extract and validate arguments from tool call, handling various formats robustly.

        The arguments field can come in different formats:
        1. As a JSON string (expected format from OpenAI API)
        2. As a dictionary (from internal processing)
        3. As None or empty (edge cases)
        """
        raw_arguments = tool_call.arguments

        # Handle None or empty arguments
        if not raw_arguments:
            self.logger.warning(f"MCP tool {self.name} called with empty arguments")
            return {}

        # Handle string arguments (JSON format)
        if isinstance(raw_arguments, str):
            try:
                parsed_arguments = json.loads(raw_arguments)
                if not isinstance(parsed_arguments, dict):
                    self.logger.warning(
                        f"MCP tool {self.name}: arguments JSON parsed to non-dict: {type(parsed_arguments)}"
                    )
                    return {}
                return parsed_arguments
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"MCP tool {self.name}: failed to parse arguments JSON '{raw_arguments}': {e}"
                )
                raise ValueError(
                    f"Invalid JSON arguments for MCP tool {self.name}: {e}"
                )

        # Handle dictionary arguments (already parsed)
        if isinstance(raw_arguments, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            self.logger.debug(f"MCP tool {self.name}: arguments already in dict format")
            return raw_arguments

        # Handle unexpected argument types
        self.logger.error(
            f"MCP tool {self.name}: unexpected arguments type {type(raw_arguments)}: {raw_arguments}"
        )
        raise ValueError(
            f"Unexpected arguments type for MCP tool {self.name}: {type(raw_arguments)}"
        )

    def _extract_structured_references(
        self, result: dict[str, Any]
    ) -> tuple[list[ContentChunk], list[ContentReference]]:
        """Opt-in: content items with valid ``unique.app/reference`` + chunk ``_meta``."""
        chunks: list[ContentChunk] = []
        references: list[ContentReference] = []
        content_items = self._extract_content_items(result)
        for item in content_items:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            meta = item.get("_meta")
            if not isinstance(meta, dict):
                continue
            ref_payload = meta.get(REFERENCE_META_KEY)
            if not isinstance(ref_payload, dict):
                continue
            try:
                reference = ContentReference.model_validate(ref_payload)
                chunk = ContentChunk.model_validate(
                    {k: v for k, v in meta.items() if k != REFERENCE_META_KEY}
                )
            except ValidationError:
                self.logger.warning(
                    "MCP tool %s: ignoring invalid %s metadata",
                    self.name,
                    REFERENCE_META_KEY,
                )
                continue
            references.append(reference)
            chunks.append(chunk)
        return chunks, references

    def _try_extract_record_references(
        self, result: dict[str, Any]
    ) -> tuple[list[ContentChunk], list[ContentReference], str | None]:
        """The tool call already succeeded, so a citation failure (such as a
        ``RecursionError`` on deeply nested JSON) falls back to the flat text."""
        try:
            return self._extract_record_references(result)
        except Exception as e:
            self.logger.warning(
                f"Could not cite the result of MCP tool {self.name}: {e!r}"
            )
            return [], [], None

    def _extract_record_references(
        self, result: dict[str, Any]
    ) -> tuple[list[ContentChunk], list[ContentReference], str | None]:
        """One chunk per record the shared extractor finds.
        Text outside those records is a system reminder, not a source."""
        content_items = self._extract_content_items(result)
        texts = [
            str(item.get("text") or "")
            for item in content_items
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        has_image = any(
            isinstance(item, dict) and item.get("type") == "image"
            for item in content_items
        )
        full_text = "\n\n".join(text for text in texts if text.strip())
        if not full_text or has_image or self._is_error_result(result):
            return [], [], None

        mapping = self._mcp_tool.reference_mapping
        items = extract_mcp_citation_items(
            {"content": content_items},
            reference_mapping=(
                mapping.model_dump(by_alias=True, exclude_none=True)
                if mapping
                else None
            ),
            fallback_text=full_text,
        )
        records = [
            (item.get("title") or self._source_name(), item.get("url"), text)
            for item in items
            if (text := item.get("text") or _link_label(item))
        ]
        if not records:
            return [], [], None
        remainder = _text_outside_records(
            texts,
            [text for item in items if (text := item.get("text"))],
            list_path=mapping.list_path if mapping else None,
        )

        chunks: list[ContentChunk] = []
        references: list[ContentReference] = []
        for index, (title, url, text) in enumerate(records):
            source_id = url or f"mcp:{self._mcp_server.name}:{self.name}:{title}"
            chunks.append(
                ContentChunk(
                    id=source_id,
                    key=title,
                    title=title,
                    text=text,
                    url=url,
                    order=index,
                )
            )
            references.append(
                ContentReference(
                    id=source_id,
                    name=title,
                    sequence_number=index + 1,
                    source=f"mcp:{self._mcp_server.name}",
                    source_id=source_id,
                    url=url,
                )
            )
        return chunks, references, remainder

    def _source_name(self) -> str:
        return self.display_name() or self.name

    @staticmethod
    def _is_error_result(result: dict[str, Any]) -> bool:
        inner = result.get("result")
        return bool(
            result.get("isError") or (isinstance(inner, dict) and inner.get("isError"))
        )

    def _process_mcp_result(self, result: dict[str, Any]) -> tuple[str, list[str]]:
        """Parse MCP result content array, upload images, return content string and data URLs."""
        content_items = self._extract_content_items(result)
        if not content_items:
            return json.dumps(result), []

        text_parts: list[str] = []
        image_data_urls: list[str] = []
        image_markdowns: list[str] = []

        for i, item in enumerate(content_items):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type", "")
            if item_type == "text":
                text_parts.append(str(item.get("text", "")))
            elif item_type == "image":
                data_b64 = item.get("data")
                mime_type = item.get("mimeType", "image/png")
                if data_b64:
                    data_url, content_id = self._process_image_content(
                        data_b64, mime_type, i
                    )
                    if data_url:
                        image_data_urls.append(data_url)
                    if content_id:
                        image_markdowns.append(
                            f"![image](unique://content/{content_id})"
                        )

        content_str = "\n\n".join(text_parts)
        if image_markdowns:
            content_str += "\n\n" + "\n\n".join(image_markdowns)
            content_str += (
                "\n\nInclude the image(s) in your response using the markdown above."
            )
        if not content_str.strip():
            content_str = json.dumps(result)
        return content_str, image_data_urls

    def _extract_content_items(self, result: dict[str, Any]) -> list[Any]:
        """Extract content array from MCP result (handles various response shapes)."""
        if "content" in result and isinstance(result["content"], list):
            return result["content"]
        if "result" in result and isinstance(result["result"], dict):
            inner = result["result"]
            if "content" in inner and isinstance(inner["content"], list):
                return inner["content"]
        return []

    def _process_image_content(
        self, data_b64: str, mime_type: str, index: int
    ) -> tuple[str | None, str | None]:
        """Decode base64 image, upload to chat, return data URL and content ID."""
        try:
            img_bytes = base64.b64decode(data_b64)
        except Exception as e:
            self.logger.warning(
                "MCP tool %s: failed to decode image base64: %s",
                self.name,
                e,
                exc_info=True,
            )
            return None, None

        data_url = f"data:{mime_type};base64,{data_b64}"
        content_id: str | None = None
        ext = mimetypes.guess_extension(mime_type, strict=False) or ".png"

        try:
            content = upload_content_from_bytes(
                user_id=self._event.user_id,
                company_id=self._event.company_id,
                content=img_bytes,
                content_name=f"mcp_tool_{self.name}_image_{uuid.uuid4().hex[:12]}_{index}{ext}",
                mime_type=mime_type,
                chat_id=self._event.payload.chat_id,
                skip_ingestion=True,
                hide_in_chat=True,
                metadata={ASSISTANT_GENERATED_METADATA_KEY: True},
            )
            content_id = content.id
        except Exception as e:
            self.logger.warning(
                "MCP tool %s: failed to upload image: %s",
                self.name,
                e,
                exc_info=True,
            )

        return data_url, content_id

    async def _call_mcp_tool_via_sdk(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call MCP tool via SDK to public API"""
        try:
            self.logger.info(
                f"Calling MCP tool {self.name} with arguments: {arguments}"
            )
            result = await unique_sdk.MCP.call_tool_async(
                user_id=self._event.user_id,
                company_id=self._event.company_id,
                name=self.name,
                messageId=self._chat_service.assistant_message_id,
                chatId=self._event.payload.chat_id,
                arguments=arguments,
            )

            self.logger.debug(f"Result: {result}")

            return result
        except Exception as e:
            self.logger.error(f"SDK call failed for MCP tool {self.name}: {e}")
            raise


def _link_label(item: dict[str, Any]) -> str | None:
    """Text for a titled link with no body, such as a ``resource_link`` without
    a description, so it is still a source the model can cite."""
    title, url = item.get("title"), item.get("url")
    return f"{title}\n{url}" if title and url else None


def _text_outside_records(
    texts: list[str],
    record_texts: list[str],
    *,
    list_path: str | None,
) -> str | None:
    """Text of the result minus the cited records, removed once per record so an
    equal value elsewhere, such as a page token, stays visible to the model."""
    full_text = "\n\n".join(text for text in texts if text.strip())
    if full_text in record_texts:
        return None
    remaining = Counter(record_texts)
    parts = [
        part
        for text in texts
        if (part := _block_outside_records(text, remaining, list_path=list_path))
    ]
    return "\n\n".join(parts) or None


def _block_outside_records(
    text: str, remaining: Counter[str], *, list_path: str | None
) -> str | None:
    if not text.strip():
        return None
    found = find_embedded_json(text)
    if found is None:
        for record_text in list(remaining):
            while remaining[record_text] > 0 and record_text in text:
                text = text.replace(record_text, "", 1)
                remaining[record_text] -= 1
        return text.strip() or None
    parsed, start, end = found
    pruned = _without_records(
        parsed, remaining, path="", list_path=list_path, in_record_list=False
    )
    body = (
        None
        if pruned is _REMOVED or not _has_value(pruned)
        else json.dumps(pruned, ensure_ascii=False, default=str)
    )
    # Text around the JSON, such as Atlassian's ``[IMPORTANT: ...]`` notice.
    parts = (text[:start].strip(), body, text[end:].strip())
    return "\n".join(part for part in parts if part) or None


_REMOVED = object()


def _without_records(
    value: Any,
    remaining: Counter[str],
    *,
    path: str,
    list_path: str | None,
    in_record_list: bool,
) -> Any:
    """``value`` without its records, or ``_REMOVED`` when the value was only records.
    A plain string is a record only inside the record list."""
    if _take_record(value, remaining, in_record_list=in_record_list):
        return _REMOVED
    if isinstance(value, dict):
        kept_dict = {
            key: kept
            for key, item in value.items()
            if (
                kept := _without_records(
                    item,
                    remaining,
                    path=f"{path}.{key}" if path else key,
                    list_path=list_path,
                    in_record_list=False,
                )
            )
            is not _REMOVED
        }
        return _REMOVED if value and not kept_dict else kept_dict
    if isinstance(value, list):
        elements_are_records = path == list_path or (list_path is None and path == "")
        kept_list = [
            kept
            for item in value
            if (
                kept := _without_records(
                    item,
                    remaining,
                    path=path,
                    list_path=list_path,
                    in_record_list=elements_are_records,
                )
            )
            is not _REMOVED
        ]
        return _REMOVED if value and not kept_list else kept_list
    return value


def _take_record(value: Any, remaining: Counter[str], *, in_record_list: bool) -> bool:
    """Matches how the extractor serializes a record into its ``text``."""
    if isinstance(value, str) and in_record_list:
        key = value
    elif isinstance(value, dict):
        key = json.dumps(value, ensure_ascii=False, default=str)
    else:
        return False
    if remaining[key] <= 0:
        return False
    remaining[key] -= 1
    return True


def _has_value(value: Any) -> bool:
    """Whether any field is left, counting an explicit ``null`` or ``""`` such as
    an end-of-pagination marker."""
    if isinstance(value, dict):
        return any(_has_value(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_value(item) for item in value)
    return True
