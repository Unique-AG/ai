import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from unique_toolkit import LanguageModelMessages
from unique_toolkit.language_model import (
    LanguageModelName,
    LanguageModelToolDescription,
)


class WeatherParameters(BaseModel):
    location: str = Field(description="The location to get the weather for")
    date: str = Field(description="The date to get the weather for")


weather_tool = LanguageModelToolDescription(
    name="weather",
    description="Get the weather in a in Paris tomorrow",
    parameters=WeatherParameters,
)


async def main():
    import unique_sdk

    messages = (
        LanguageModelMessages([])
        .builder()
        .system_message_append("You are a helpful assistant")
        .user_message_append("What is the weather in Paris tomorrow?")
        .build()
    )
    load_dotenv(Path(__file__).parent / ".." / ".env")

    unique_sdk.api_key = os.getenv("API_KEY", "dummy")
    unique_sdk.app_id = os.getenv("APP_ID", "dummy")
    unique_sdk.api_base = os.getenv("API_BASE", "dummy")
    company_id = os.getenv("COMPANY_ID", "dummy")

    from unique_toolkit.language_model.functions import _add_tools_to_options

    options = _add_tools_to_options({}, [weather_tool])

    result = await unique_sdk.ChatCompletion.create_async(
        company_id=company_id,
        model=LanguageModelName.AZURE_GPT_4o_2024_0806,
        messages=messages.model_dump(mode="json"),
        options=options,
    )
    print(result["choices"][0]["message"]["toolCalls"])


if __name__ == "__main__":
    asyncio.run(main())
