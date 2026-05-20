"""Briefing CRUD.

Create (upsert), retrieve, and delete an assistant briefing via unique_sdk.

Run from the ``unique_sdk`` package directory::

    uv run python examples/basics/briefing_crud.py
"""

import logging
import os
import sys
from logging import getLogger
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


def main() -> None:
    import unique_sdk

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    unique_sdk.api_key = os.getenv("API_KEY", "")
    unique_sdk.app_id = os.getenv("APP_ID", "")
    api_base = os.getenv("API_BASE")
    if api_base:
        unique_sdk.api_base = api_base.rstrip("/")

    user_id = os.getenv("USER_ID", "")
    company_id = os.getenv("COMPANY_ID", "")
    assistant_id = os.getenv("ASSISTANT_ID", "")

    if not all((unique_sdk.api_key, unique_sdk.app_id, user_id, company_id)):
        logger.error("Set API_KEY, APP_ID, USER_ID, and COMPANY_ID in unique_sdk/.env")
        sys.exit(1)
    if not assistant_id:
        logger.error("Set ASSISTANT_ID in .env to the target assistant (space) id.")
        sys.exit(1)

    generated_at = "2026-05-20T07:00:00.000Z"
    text = "## Market overview\nKey themes from overnight news…"
    prompts: list[unique_sdk.Briefing.BriefingPromptItem] = [
        {"title": "Summarise", "body": "Give me a one-paragraph summary."},
        {"title": "Deep dive", "body": "Which story deserves more attention?"},
    ]

    logger.info("Upsert briefing on assistant %s", assistant_id)
    briefing = unique_sdk.Briefing.upsert_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
        text=text,
        title="Today's Briefing",
        generatedAt=generated_at,
        prompts=prompts,
    )
    logger.info("Upserted text preview: %s…", (briefing.get("text") or "")[:60])

    logger.info("Retrieve briefing")
    loaded = unique_sdk.Briefing.retrieve_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    logger.info(
        "Retrieved prompts=%s title=%r",
        len(loaded.get("prompts") or []),
        loaded.get("title"),
    )

    logger.info("Delete briefing attachment")
    result = unique_sdk.Briefing.delete_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    logger.info("Deleted=%s id=%r", result.get("deleted"), result.get("id"))


if __name__ == "__main__":
    main()
