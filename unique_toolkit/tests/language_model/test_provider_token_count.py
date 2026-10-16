from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat import ChatCompletionMessageParam

from unique_toolkit.language_model.functions import (
    count_tokens_with_provider_async,
)
from unique_toolkit.language_model.provider_token_count import (
    build_provider_token_count_payload,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelAssistantMessage,
    LanguageModelFunction,
    LanguageModelMessages,
    LanguageModelToolMessage,
    LanguageModelUserMessage,
)


@pytest.mark.ai
def test_build_provider_token_count_payload__converts_tools_and_results_AI() -> None:
    """
    Purpose: Build the provider counter payload from the chat-completions representation.
    Why this matters: Anthropic's counter must see tool schemas, calls and large results.
    Setup summary: System + parallel tool calls + results -> Anthropic-compatible messages.
    """
    messages = cast(
        "list[ChatCompletionMessageParam]",
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "search"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "type": "function",
                        "id": "call_1",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "one"}',
                        },
                    },
                    {
                        "type": "function",
                        "id": "call_2",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "two"}',
                        },
                    },
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": "result one"},
            {"role": "tool", "tool_call_id": "call_2", "content": "result two"},
        ],
    )
    tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            },
        }
    ]

    payload = build_provider_token_count_payload(
        model="litellm:claude-sonnet-5-5",
        messages=messages,
        tools=tools,
    )

    assert payload["model"] == "claude-sonnet-5-5"
    assert payload["system"] == "system"
    assert payload["tools"] == [
        {
            "name": "search",
            "description": "Search",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
    ]
    assert payload["messages"][1]["content"][0] == {
        "type": "tool_use",
        "id": "call_1",
        "name": "search",
        "input": {"query": "one"},
    }
    assert payload["messages"][2] == {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "call_1",
                "content": "result one",
            },
            {
                "type": "tool_result",
                "tool_use_id": "call_2",
                "content": "result two",
            },
        ],
    }


@pytest.mark.ai
@pytest.mark.asyncio
async def test_count_tokens_with_provider_async__returns_proxy_count_AI() -> None:
    """
    Purpose: Send the transformed completion payload through the authenticated SDK endpoint.
    Why this matters: The preflight guard must use provider counts without direct provider credentials.
    Setup summary: One user message, provider returns 123 tokens -> helper returns 123.
    """
    with patch(
        "unique_toolkit.language_model.functions.unique_sdk.Integrated.count_tokens_async",
        AsyncMock(return_value={"input_tokens": 123}),
    ) as count_tokens:
        result = await count_tokens_with_provider_async(
            company_id="company_1",
            user_id="user_1",
            messages=cast(
                "list[ChatCompletionMessageParam]",
                [{"role": "user", "content": "Hello"}],
            ),
            model_name="litellm:claude-sonnet-5-5",
        )

    assert result == 123
    count_tokens.assert_awaited_once()
    assert count_tokens.await_args.kwargs["model"] == "claude-sonnet-5-5"
    assert count_tokens.await_args.kwargs["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
    ]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_count_tokens_with_provider_async__preserves_camelcase_tool_and_image_fields_AI() -> (
    None
):
    """
    Purpose: Preserve tool calls, tool call IDs and tool image parts produced by LanguageModelMessages.
    Why this matters: _prepare_all_completions_params_util camelizes keys before building the payload.
    Setup summary: LanguageModelMessages with assistant tool_calls, tool result and imageUrl part -> included in payload.
    """
    messages = LanguageModelMessages(
        [
            LanguageModelUserMessage(
                content=[
                    {"type": "text", "text": "Inspect"},
                    {
                        "type": "image_url",
                        "imageUrl": {"url": "data:image/png;base64,aGVsbG8="},
                    },
                ]
            ),
            LanguageModelAssistantMessage.from_functions(
                tool_calls=[
                    LanguageModelFunction(
                        id="call_1",
                        name="search",
                        arguments='{"query": "one"}',
                    )
                ]
            ),
            LanguageModelToolMessage(
                tool_call_id="call_1",
                name="search",
                content="result one",
            ),
        ]
    )

    with patch(
        "unique_toolkit.language_model.functions.unique_sdk.Integrated.count_tokens_async",
        AsyncMock(return_value={"input_tokens": 456}),
    ) as count_tokens:
        result = await count_tokens_with_provider_async(
            company_id="company_1",
            user_id="user_1",
            messages=messages,
            model_name="litellm:claude-sonnet-5-5",
        )

    assert result == 456
    sent_messages = count_tokens.await_args.kwargs["messages"]
    assert sent_messages[0]["content"][1] == {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "aGVsbG8=",
        },
    }
    assert sent_messages[1]["content"] == [
        {
            "type": "tool_use",
            "id": "call_1",
            "name": "search",
            "input": {"query": "one"},
        }
    ]
    assert sent_messages[2]["content"] == [
        {
            "type": "tool_result",
            "tool_use_id": "call_1",
            "content": "result one",
        }
    ]
