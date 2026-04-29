#!/usr/bin/env python3
"""Manual smoke test for Briefing.upsert_for_assistant.

Edit the constants below, then from the ``unique_sdk`` package root::

    uv run python examples/briefing_manual_smoke.py

Delete when done. Do not commit real secrets.
"""

from __future__ import annotations

import json
import pprint

import unique_sdk
from unique_sdk import APIError, AuthenticationError, InvalidRequestError

# --- Edit these (use placeholders in shared copies). Do not commit real secrets ---
UNIQUE_APP_KEY = "CHANGEME_APP_KEY"
UNIQUE_APP_ID = "CHANGEME_APP_ID"
UNIQUE_API_BASE_URL = "https://gateway.qa.unique.app/public/chat-gen2"
UNIQUE_AUTH_COMPANY_ID = "CHANGEME_COMPANY_ID"
UNIQUE_AUTH_USER_ID = "CHANGEME_USER_ID"

# Path param: assistant the briefing attaches to (OpenAPI assistantId, max 128 chars)
UNIQUE_ASSISTANT_ID = "CHANGEME_ASSISTANT_ID"

UNIQUE_BRIEFING_TEXT = (
    "# Smoke test\n\n"
    "Briefing manual smoke (PublicUpsertBriefingRequestDto: text, generatedAt, prompts).\n"
)
# ISO 8601 timestamp for this revision, or None to let the SDK stamp UTC now()
UNIQUE_BRIEFING_GENERATED_AT: str | None = None

# Full replacement set of prompts (max 200). Order is persisted as returned.
UNIQUE_BRIEFING_PROMPTS = [
    {"title": "Example prompt title", "body": "Example prompt body."},
]


def main() -> None:
    unique_sdk.api_key = UNIQUE_APP_KEY
    unique_sdk.app_id = UNIQUE_APP_ID
    unique_sdk.api_base = UNIQUE_API_BASE_URL

    kwargs: dict = {
        "user_id": UNIQUE_AUTH_USER_ID,
        "company_id": UNIQUE_AUTH_COMPANY_ID,
        "assistant_id": UNIQUE_ASSISTANT_ID,
        "text": UNIQUE_BRIEFING_TEXT,
        "prompts": UNIQUE_BRIEFING_PROMPTS,
    }
    if UNIQUE_BRIEFING_GENERATED_AT:
        kwargs["generatedAt"] = UNIQUE_BRIEFING_GENERATED_AT

    briefing = unique_sdk.Briefing.upsert_for_assistant(**kwargs)

    print("Briefing upsert succeeded. Response:")
    pprint.pp(dict(briefing))


if __name__ == "__main__":
    try:
        main()
    except InvalidRequestError as exc:
        print(f"HTTP {exc.http_status}: {exc}")
        print("params:", getattr(exc, "params", None))
        if exc.json_body is not None:
            print("json_body:", json.dumps(exc.json_body, indent=2, default=str))
        if exc.http_body:
            print("http_body:", exc.http_body)
        raise SystemExit(1) from exc
    except AuthenticationError as exc:
        print(f"Unauthorized (HTTP {exc.http_status}): {exc}")
        if exc.json_body is not None:
            print("json_body:", json.dumps(exc.json_body, indent=2, default=str))
        print()
        print(
            "401 usually means credentials or environment mismatch. Check:\n"
            "  - UNIQUE_APP_KEY / UNIQUE_APP_ID match a valid app for this "
            "gateway (e.g. QA keys with https://gateway.qa…. …/chat-gen2).\n"
            "  - UNIQUE_AUTH_USER_ID and UNIQUE_AUTH_COMPANY_ID are correct "
            "for that app (no typos).\n"
            "  - The key is not expired or revoked.",
        )
        raise SystemExit(1) from exc
    except APIError as exc:
        print(f"API error (HTTP {exc.http_status}): {exc}")
        if exc.json_body is not None:
            print("json_body:", json.dumps(exc.json_body, indent=2, default=str))
        raise SystemExit(1) from exc
