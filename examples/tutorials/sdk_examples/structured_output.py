import os
from typing import Any

from pydantic import BaseModel, Field


def _add_response_format_to_options(
    options: dict[str, Any],
    structured_output_model: type[BaseModel],
    structured_output_enforce_schema: bool = False,
) -> dict:
    options["responseFormat"] = {
        "type": "json_schema",
        "json_schema": {
            "name": structured_output_model.__name__,
            "strict": structured_output_enforce_schema,
            "schema": structured_output_model.model_json_schema(),
        },
    }
    return options


class Person(BaseModel):
    name: str = Field(..., description="The Name of a person")
    age: int = Field(..., description="The age of a person")


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    import unique_sdk

    load_dotenv(Path(__file__).parent / ".." / ".env.api_key")
    unique_sdk.api_key = os.getenv("API_KEY", "")
    unique_sdk.app_id = os.getenv("APP_ID", "")
    unique_sdk.api_base = os.getenv("API_BASE", "")
    company_id = os.getenv("COMPANY_ID", "")

    messages = [
        {"role": "system", "content": "You help to extract users from data"},
        {
            "role": "user",
            "content": "John Doe is 30 years old",
        },
    ]

    # Prepare options for structured output
    options: dict[str, Any] = {}
    options = _add_response_format_to_options(options, Person)
    options["temperature"] = 0

    response = unique_sdk.ChatCompletion.create(
        company_id=company_id,
        model="AZURE_GPT_4o_2024_0806",
        messages=messages,
        timeout=24_000,
        options=options,
    )
    print(response["choices"][0]["message"]["parsed"])
