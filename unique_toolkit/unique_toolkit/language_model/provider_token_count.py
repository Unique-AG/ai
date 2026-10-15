from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any


def build_provider_token_count_payload(
    *,
    model: str,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Convert an OpenAI chat payload to LiteLLM's Anthropic-compatible counter."""
    system_parts: list[str] = []
    provider_messages: list[dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        if role == "system":
            content = message.get("content")
            if isinstance(content, str) and content:
                system_parts.append(content)
            continue

        if role == "assistant":
            blocks = _assistant_content_blocks(message)
            _append_message(provider_messages, "assistant", blocks)
        elif role == "tool":
            _append_message(
                provider_messages,
                "user",
                [
                    {
                        "type": "tool_result",
                        "tool_use_id": (
                            message.get("tool_call_id")
                            or message.get("toolCallId")
                            or ""
                        ),
                        "content": _content_as_text(message.get("content")),
                    }
                ],
            )
        elif role == "user":
            _append_message(
                provider_messages,
                "user",
                _user_content_blocks(message.get("content")),
            )

    payload: dict[str, Any] = {
        "model": model.removeprefix("litellm:"),
        "messages": provider_messages,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)
    if tools:
        payload["tools"] = [_anthropic_tool(tool) for tool in tools]
    return payload


def _assistant_content_blocks(
    message: Mapping[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    content = message.get("content")
    if isinstance(content, str) and content:
        blocks.append({"type": "text", "text": content})

    tool_calls = message.get("tool_calls") or message.get("toolCalls")
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            if not isinstance(function, dict):
                continue
            blocks.append(
                {
                    "type": "tool_use",
                    "id": tool_call.get("id", ""),
                    "name": function.get("name", ""),
                    "input": _tool_arguments(function.get("arguments")),
                }
            )
    return blocks


def _user_content_blocks(content: object) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return [{"type": "text", "text": ""}]

    blocks: list[dict[str, Any]] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text":
            blocks.append({"type": "text", "text": str(part.get("text", ""))})
        elif part.get("type") == "image_url":
            image_url = part.get("image_url") or part.get("imageUrl")
            if isinstance(image_url, dict):
                image_block = _base64_image_block(image_url.get("url"))
                if image_block is not None:
                    blocks.append(image_block)
    return blocks or [{"type": "text", "text": ""}]


def _base64_image_block(url: object) -> dict[str, Any] | None:
    if not isinstance(url, str) or not url.startswith("data:") or ";base64," not in url:
        return None
    metadata, data = url.split(";base64,", 1)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": metadata.removeprefix("data:"),
            "data": data,
        },
    }


def _append_message(
    messages: list[dict[str, Any]],
    role: str,
    blocks: list[dict[str, Any]],
) -> None:
    if messages and messages[-1]["role"] == role:
        messages[-1]["content"].extend(blocks)
        return
    messages.append({"role": role, "content": blocks})


def _anthropic_tool(tool: Mapping[str, Any]) -> dict[str, Any]:
    function = tool.get("function", tool)
    if not isinstance(function, dict):
        function = {}
    return {
        "name": function.get("name", ""),
        "description": function.get("description", ""),
        "input_schema": function.get(
            "parameters", {"type": "object", "properties": {}}
        ),
    }


def _tool_arguments(arguments: object) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"raw": arguments}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _content_as_text(content: object) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content)
