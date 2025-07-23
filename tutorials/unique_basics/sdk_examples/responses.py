"""Responses API

The following tutorial shows how to use Responses API to stream in a chat.
"""

import logging
import os
from logging import getLogger
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


def main():
    """
    Example of using the Responses API to stream in a chat.
    """
    import unique_sdk

    # Load environment variables
    load_dotenv(Path(__file__).parent / ".." / ".env")

    # Set up SDK configuration
    unique_sdk.api_key = os.getenv("API_KEY")
    unique_sdk.app_id = os.getenv("APP_ID")
    unique_sdk.api_base = os.getenv("API_BASE")
    company_id = os.getenv("COMPANY_ID")
    user_id = os.getenv("USER_ID")

    # Example: Call Responses API to create a basic response.
    try:
        responses = unique_sdk.Responses.create(
            company_id=company_id,
            user_id=user_id,
            input="Tell me about the curious case of neural text degeneration",
            model="AZURE_o3_2025_0416",
            reasoning={
                "effort": "medium",  # effort level: low | medium | high
                "summary": "detailed",  # summary type: auto | concise | detailed
            },
        )
        logger.info(f"Responses API successfully created a response: {responses}")
    except Exception as e:
        logger.error(f"Failed to create a response using Response API: {e}")


if __name__ == "__main__":
    main()
