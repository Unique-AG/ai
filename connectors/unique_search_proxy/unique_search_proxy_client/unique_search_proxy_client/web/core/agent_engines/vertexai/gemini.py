from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from google.genai import types
from google.genai.client import AsyncClient
from pydantic import BaseModel


def _get_grounding_tool(*, use_enterprise_search: bool = False) -> types.Tool:
    if use_enterprise_search:
        return types.Tool(enterprise_web_search=types.EnterpriseWebSearch())
    return types.Tool(google_search=types.GoogleSearch())


def build_generate_content_config(
    *,
    generation_instructions: str,
    output_schema: type[BaseModel],
    enable_enterprise_search: bool = False,
) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[_get_grounding_tool(use_enterprise_search=enable_enterprise_search)],
        system_instruction=generation_instructions,
        response_mime_type="application/json",
        response_schema=output_schema,
    )


async def generate_vertexai_response(
    *,
    client: AsyncClient,
    model_name: str,
    config: types.GenerateContentConfig,
    contents: str,
) -> types.GenerateContentResponse:
    return await client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
    )


async def stream_vertexai_response(
    *,
    client: AsyncClient,
    model_name: str,
    config: types.GenerateContentConfig,
    contents: str,
) -> AsyncIterator[types.GenerateContentResponse]:
    stream = await client.models.generate_content_stream(
        model=model_name,
        contents=contents,
        config=config,
    )
    async for chunk in stream:
        yield chunk


def serialize_vertex_response(response: types.GenerateContentResponse) -> Any:
    return response.model_dump(mode="json")
