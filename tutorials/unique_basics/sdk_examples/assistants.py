"""Assistants API examples.

The following tutorial shows how to use Assistants API.
"""

import asyncio
import logging
import os
from logging import getLogger
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


async def main():
    import unique_sdk

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".." / ".env")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY")
    unique_sdk.app_id = os.getenv("APP_ID")
    unique_sdk.api_base = os.getenv("API_BASE")
    company_id = os.getenv("COMPANY_ID")
    user_id = os.getenv("USER_ID")

    # Example: Using code interpreter
    try:
        assistant = await unique_sdk.Assistants.create_async(
            company_id=company_id,
            user_id=user_id,
            name="Math Tutor",
            model="AZURE_o1_2024_1217",
            instructions="You are a personal math tutor. When asked a question, write and run Python code to solve it. If the question is not related to math, politely decline to answer.",
            tools=[
                {
                    "type": "code_interpreter",
                }
            ],
        )

        thread = await unique_sdk.Assistants.create_thread_async(
            company_id=company_id,
            user_id=user_id,
        )

        await unique_sdk.Assistants.create_message_async(
            company_id=company_id,
            user_id=user_id,
            thread_id=thread.id,
            content="I need to solve the equation 3x + 4 - 10 = 24",
            role="user",
        )

        run = await unique_sdk.Assistants.create_run_async(
            company_id=company_id,
            user_id=user_id,
            model="AZURE_o1_2024_1217",
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        while run.status not in ["completed", "failed"]:
            run = await unique_sdk.Assistants.retrieve_run_async(
                company_id=company_id,
                user_id=user_id,
                thread_id=thread.id,
                run_id=run.id,
            )

        messages = await unique_sdk.Assistants.list_messages_async(
            company_id=company_id,
            user_id=user_id,
            thread_id=thread.id,
        )

        # print("folder")
        print(messages)
        logger.info(f"Successful retrieval of messages: {messages}")
    except Exception as e:
        logger.error(f"Failed to retrieve messages: {e}")


if __name__ == "__main__":
    asyncio.run(main())
