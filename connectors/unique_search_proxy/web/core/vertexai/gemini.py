from google.genai import types
from google.genai.client import AsyncClient

from core.vertexai.response_handler import (
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
    response = await client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
    )

    return post_process_function(response)
