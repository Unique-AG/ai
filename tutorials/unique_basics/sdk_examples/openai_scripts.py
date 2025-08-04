"""OpenAI SDK Examples.

This script demonstrates how to use the OpenAI SDK with Unique API proxy for:
- Chat Completions
- Assistants
- Responses

Make sure to adjust the model based on the API used and your needs.

Usage:
    poetry run python sdk_examples/openai_scripts.py chat
    poetry run python sdk_examples/openai_scripts.py assistants
    poetry run python sdk_examples/openai_scripts.py responses
"""

import logging
import os
import sys

from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_client_and_headers():
    # Set up SDK configuration
    model = "AZURE_o3_2025_0416"

    ## The API base URL should point to your Unique API proxy and should look like:
    ## {your_base_url}/openai-proxy/
    ## For example: https://gateway.us.unique.app/public/openai-proxy/
    api_base = os.getenv("API_BASE", "http://localhost:8092/public/")

    company_id = os.getenv("COMPANY_ID")
    user_id = os.getenv("USER_ID")
    model = os.getenv("MODEL")
    app_id = os.getenv("APP_ID")
    api_key = os.getenv("API_KEY")

    client = OpenAI(
        api_key="dummy",  # Using a dummy key since we're using custom auth
        base_url=api_base + "openai-proxy/",
    )

    extra_headers = {
        "x-user-id": user_id,
        "x-company-id": company_id,
        "x-api-version": "2023-12-06",
        "x-app-id": app_id,
        "x-model": model,
        "Authorization": f"Bearer {api_key}",
    }
    return client, extra_headers, model


def run_chat_completions():
    client, extra_headers, model = get_client_and_headers()
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "How is the weather in New York"},
    ]
    logger.info("Running chat completions...")
    try:
        response = client.chat.completions.create(
            extra_headers=extra_headers,
            messages=messages,
            model=model,
        )
        logger.info("Chat completion response:")
        print(response)
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")


def run_assistants():
    client, extra_headers, model = get_client_and_headers()
    logger.info("Running assistant flow...")
    try:
        assistant = client.beta.assistants.create(
            extra_headers=extra_headers,
            name="My Assistant",
            model=model,
            instructions="You are a personal math tutor. When asked a question, write and run Python code to solve it. If the question is not related to math, politely decline to answer.",
            tools=[
                {
                    "type": "code_interpreter",
                }
            ],
        )
        thread = client.beta.threads.create(extra_headers=extra_headers)
        logger.info(f"Created assistant: {assistant.id}")
        logger.info(f"Created thread: {thread.id}")

        client.beta.threads.messages.create(
            extra_headers=extra_headers,
            thread_id=thread.id,
            content="I need to solve the equation 3x + 4 - 10 = 24",
            role="user",
        )

        run = client.beta.threads.runs.create(
            extra_headers=extra_headers,
            model=model,
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        logger.info(f"Created run: {run.id}")

        # Poll for completion
        while run.status not in ["completed", "failed"]:
            run = client.beta.threads.runs.retrieve(
                extra_headers=extra_headers,
                thread_id=thread.id,
                run_id=run.id,
            )
            logger.info(f"Run status: {run.status}")

        messages = client.beta.threads.messages.list(
            extra_headers=extra_headers,
            thread_id=thread.id,
        )
        logger.info("Assistant messages:")
        print(messages)
    except Exception as e:
        logger.error(f"Assistant flow failed: {e}")


def run_responses():
    client, extra_headers, model = get_client_and_headers()
    logger.info("Running responses flow...")
    logger.info(extra_headers)
    try:
        response = client.responses.create(
            extra_headers=extra_headers,
            model=model,
            input="Tell me a three sentence bedtime story about a unicorn.",
        )
        logger.info("Response:")
        print(response)
    except Exception as e:
        logger.error(f"Responses flow failed: {e}")


def main():
    from dotenv import load_dotenv

    load_dotenv("./.env")
    if len(sys.argv) < 2:
        logger.error("Please provide a flow to run: chat, assistant, or response")
        sys.exit(1)
    flow = sys.argv[1].lower()
    if flow == "chat":
        run_chat_completions()
    elif flow == "assistants":
        run_assistants()
    elif flow == "responses":
        run_responses()
    else:
        logger.error("Unknown flow. Use one of: chat, assistants, responses")
        sys.exit(1)


if __name__ == "__main__":
    main()
