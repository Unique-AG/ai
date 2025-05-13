"""Rate limited requests.

The following tutorial shows how to limit the number of requests to the
llm to avoid the rate limits
"""

import asyncio
import logging
import os
from logging import getLogger
from pathlib import Path

from aiolimiter import AsyncLimiter
from dotenv import load_dotenv
from utilities_examples.async_helpers import execute_multiple_coros

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


async def main():
    import unique_sdk

    load_dotenv(Path(__file__).parent / ".." / ".env")

    unique_sdk.api_key = os.getenv("API_KEY", "dummy")
    unique_sdk.app_id = os.getenv("APP_ID", "dummy")
    unique_sdk.api_base = os.getenv("API_BASE", "dummy")
    company_id = os.getenv("COMPANY_ID", "dummy")

    max_token_per_minute = 30_000
    max_token_per_request = 500
    estimated_time_per_request_in_seconds = 10

    rate_limiter = AsyncLimiter(
        max_rate=max_token_per_minute // max_token_per_request,
        time_period=estimated_time_per_request_in_seconds,
    )

    coros = [
        unique_sdk.ChatCompletion.create_async(
            company_id=company_id,
            model="AZURE_GPT_4_0613",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"What follows after the number {i}. Answer with the number only.",
                },
            ],
        )
        for i in range(10)
    ]

    results = await execute_multiple_coros(
        coros,
        lambda result: logger.info(
            f"Task finished with result: {result['choices'][0]['message']['content']}"
        ),
        limiter=rate_limiter,
    )

    for i, res in enumerate(results):
        logger.info(f"Task {i} final result: {res['choices'][0]['message']['content']}")


if __name__ == "__main__":
    asyncio.run(main())
