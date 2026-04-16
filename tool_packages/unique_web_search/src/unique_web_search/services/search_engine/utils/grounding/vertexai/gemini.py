from google.genai import types
from google.genai.client import AsyncClient


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
