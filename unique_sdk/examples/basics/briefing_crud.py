"""Briefing CRUD.

Create (upsert), retrieve, and delete an assistant briefing via unique_sdk.

Run from the ``unique_sdk`` project directory::

    uv run python examples/basics/briefing_crud.py
"""

from __future__ import annotations

import logging
import os
import sys
from logging import getLogger

from sdk_env import configure_sdk

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)


def main() -> None:
    import unique_sdk

    config = configure_sdk()
    assistant_id = os.getenv("ASSISTANT_ID", "")
    if not assistant_id:
        logger.error(
            "Set ASSISTANT_ID in examples/basics/.env to the target assistant (space) id."
        )
        sys.exit(1)

    generated_at = "2026-05-20T07:00:00.000Z"
    text = "## Market overview\nKey themes from overnight news…"
    prompts: list[unique_sdk.Briefing.BriefingPromptItem] = [
        {"title": "Summarise", "body": "Give me a one-paragraph summary."},
        {"title": "Deep dive", "body": "Which story deserves more attention?"},
    ]

    logger.info("Upsert briefing on assistant %s", assistant_id)
    try:
        briefing = unique_sdk.Briefing.upsert_for_assistant(
            user_id=config.user_id,
            company_id=config.company_id,
            assistant_id=assistant_id,
            text=text,
            title="Today's Briefing",
            generatedAt=generated_at,
            prompts=prompts,
        )
    except unique_sdk.AuthenticationError as exc:
        logger.error(
            "401 Unauthorized — the gateway rejected your credentials. "
            "Use a valid ukey_ API key and matching UNIQUE_APP_ID, "
            "UNIQUE_AUTH_USER_ID, and UNIQUE_AUTH_COMPANY_ID for the same tenant; "
            "UNIQUE_API_BASE_URL must target the same environment (prod vs QA). "
            "Generate or rotate keys in the Unique admin UI if needed."
        )
        raise exc
    logger.info("Upserted text preview: %s…", (briefing.get("text") or "")[:60])

    logger.info("Retrieve briefing")
    loaded = unique_sdk.Briefing.retrieve_for_assistant(
        user_id=config.user_id,
        company_id=config.company_id,
        assistant_id=assistant_id,
    )
    logger.info(
        "Retrieved prompts=%s title=%r",
        len(loaded.get("prompts") or []),
        loaded.get("title"),
    )

    logger.info("Delete briefing attachment")
    result = unique_sdk.Briefing.delete_for_assistant(
        user_id=config.user_id,
        company_id=config.company_id,
        assistant_id=assistant_id,
    )
    logger.info("Deleted=%s id=%r", result.get("deleted"), result.get("id"))


if __name__ == "__main__":
    main()
