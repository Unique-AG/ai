#!/usr/bin/env python3
"""Create, retrieve, and delete an assistant briefing via unique_sdk.

Requires API credentials and an assistant (space) id. Run from the ``unique_sdk``
package directory:

    uv run python examples/briefing_crud.py

Environment variables (``UNIQUE_*`` preferred; ``API_*`` aliases also accepted):

    UNIQUE_API_KEY / API_KEY
    UNIQUE_APP_ID / APP_ID
    UNIQUE_USER_ID / USER_ID
    UNIQUE_COMPANY_ID / COMPANY_ID
    UNIQUE_API_BASE / API_BASE  (optional; defaults to gateway chat-gen2 path)
    ASSISTANT_ID                (required — assistant the briefing attaches to)
"""

from __future__ import annotations

import os
import sys

import unique_sdk


def _env(name: str, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.getenv(key)
        if value:
            return value
    return None


def _configure_sdk() -> tuple[str, str]:
    api_key = _env("UNIQUE_API_KEY", "API_KEY")
    app_id = _env("UNIQUE_APP_ID", "APP_ID")
    user_id = _env("UNIQUE_USER_ID", "USER_ID")
    company_id = _env("UNIQUE_COMPANY_ID", "COMPANY_ID")
    api_base = _env("UNIQUE_API_BASE", "API_BASE")

    missing = [
        label
        for label, value in (
            ("UNIQUE_API_KEY (or API_KEY)", api_key),
            ("UNIQUE_APP_ID (or APP_ID)", app_id),
            ("UNIQUE_USER_ID (or USER_ID)", user_id),
            ("UNIQUE_COMPANY_ID (or COMPANY_ID)", company_id),
        )
        if not value
    ]
    if missing:
        print(
            "Missing required environment variables:",
            ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)

    unique_sdk.api_key = api_key
    unique_sdk.app_id = app_id
    if api_base:
        unique_sdk.api_base = api_base.rstrip("/")

    assert user_id is not None and company_id is not None
    return user_id, company_id


def main() -> None:
    user_id, company_id = _configure_sdk()

    assistant_id = _env("ASSISTANT_ID")
    if not assistant_id:
        print("Set ASSISTANT_ID to the target assistant (space) id.", file=sys.stderr)
        sys.exit(1)

    generated_at = "2026-05-20T07:00:00.000Z"
    text = "## Market overview\nKey themes from overnight news…"
    prompts: list[unique_sdk.Briefing.BriefingPromptItem] = [
        {"title": "Summarise", "body": "Give me a one-paragraph summary."},
        {"title": "Deep dive", "body": "Which story deserves more attention?"},
    ]

    print(f"1. Upsert briefing on assistant {assistant_id!r} …")
    briefing = unique_sdk.Briefing.upsert_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
        text=text,
        title="Today's Briefing",
        generatedAt=generated_at,
        prompts=prompts,
    )
    print(f"   text preview: {briefing.get('text', '')[:60]!r} …")

    print("2. Retrieve briefing …")
    loaded = unique_sdk.Briefing.retrieve_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    prompt_count = len(loaded.get("prompts") or [])
    print(f"   prompts={prompt_count}, title={loaded.get('title')!r}")

    print("3. Delete briefing attachment …")
    result = unique_sdk.Briefing.delete_for_assistant(
        user_id=user_id,
        company_id=company_id,
        assistant_id=assistant_id,
    )
    print(f"   deleted={result.get('deleted')}, id={result.get('id')!r}")

    print("Done.")


if __name__ == "__main__":
    main()
