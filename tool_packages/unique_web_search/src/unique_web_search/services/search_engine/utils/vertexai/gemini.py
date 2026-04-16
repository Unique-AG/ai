from google.genai import types
from google.genai.client import AsyncClient

from unique_web_search.services.search_engine.utils.vertexai.response_handler import (
    PostProcessFunction,
    T,
)


async def generate_content(
    *,
    client: AsyncClient,
    model_name: str,
    config: types.GenerateContentConfig,
    contents: str,
    post_process_function: PostProcessFunction[T],
) -> T:
    response = await raw_generate_content(
        client=client,
        model_name=model_name,
        config=config,
        contents=contents,
    )

    return post_process_function(response)


async def raw_generate_content(
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
