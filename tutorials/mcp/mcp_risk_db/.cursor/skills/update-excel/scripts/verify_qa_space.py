# /// script
# requires-python = ">=3.11"
# dependencies = ["unique-sdk>=2026.38.0"]
# ///
"""Verify the deployed Risk DB MCP through a QA Unique AI space."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys

import unique_sdk
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

QA_API_BASE = "https://gateway.qa.unique.app/public/chat-gen2"
QA_USER_ID = "353194960666759723"
QA_COMPANY_ID = "225319369280852798"
QA_APP_ID = "app_le7m7o2w3zurin746dpx88ro"
QA_ASSISTANT_ID = "assistant_a9csiq8hbd10xnojpqlk6980"
KEYCHAIN_SERVICE = "unique-qa-public-api"
EXPECTED_VALUES = ("2026-09-22", "1746.3", "780.7", "79.6", "167.9")
CONNECTION_ERROR_MARKERS = (
    "mcp server not found",
    "session expired",
    "reconnect to continue",
)

PROMPT = """Call the connected Risk DB MCP query_data tool. Do not answer from memory.

Use these exact arguments:
- sheet_name: pnl_daily
- filters: {"date": "2026-09-22"}
- columns: ["fund_id", "date", "net_pnl_mm", "cum_ytd_pnl_mm"]
- limit: 10

Return the tool result and explicitly state whether matching rows were found."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query the QA Risk DB demo space and verify the new workbook data."
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Print the response without asserting the updated values.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Maximum seconds to wait for the assistant response.",
    )
    return parser.parse_args()


def read_api_key(app_id: str) -> str:
    environment_key = os.getenv("UNIQUE_API_KEY")
    if environment_key:
        return environment_key

    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-s",
            KEYCHAIN_SERVICE,
            "-a",
            app_id,
            "-w",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "QA API key not found in Keychain. Store it under service "
            f"{KEYCHAIN_SERVICE!r} and account {app_id!r}."
        )
    return result.stdout.strip()


async def verify_qa_space(observe: bool, timeout: float) -> int:
    app_id = os.getenv("UNIQUE_APP_ID", QA_APP_ID)
    unique_sdk.api_base = os.getenv("UNIQUE_API_BASE", QA_API_BASE)
    unique_sdk.app_id = app_id
    unique_sdk.api_key = read_api_key(app_id)

    response = await send_message_and_wait_for_completion(
        user_id=os.getenv("UNIQUE_USER_ID", QA_USER_ID),
        company_id=os.getenv("UNIQUE_COMPANY_ID", QA_COMPANY_ID),
        assistant_id=os.getenv("UNIQUE_ASSISTANT_ID", QA_ASSISTANT_ID),
        text=PROMPT,
        poll_interval=2,
        max_wait=timeout,
        stop_condition="completedAt",
    )
    answer = response.get("text") or ""
    print(answer)

    if observe:
        return 0

    normalized_answer = answer.replace(",", "")
    if any(marker in normalized_answer.lower() for marker in CONNECTION_ERROR_MARKERS):
        print(
            "Verification blocked: open the QA space and manually reconnect the "
            "Risk DB MCP, then rerun this script.",
            file=sys.stderr,
        )
        return 2

    missing_values = [
        value for value in EXPECTED_VALUES if value not in normalized_answer
    ]
    if missing_values:
        print(
            "Verification failed: response is missing expected updated values: "
            + ", ".join(missing_values),
            file=sys.stderr,
        )
        return 1

    print("Verification passed: QA returned the 2026-09-22 Risk DB data.")
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(verify_qa_space(args.observe, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
