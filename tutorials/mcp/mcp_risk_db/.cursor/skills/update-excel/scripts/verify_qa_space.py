# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1", "pandas>=2.0", "unique-sdk>=2026.38.0"]
# ///
"""Verify the deployed Risk DB MCP through a QA Unique AI space."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import unique_sdk
from unique_sdk.utils.chat_in_space import send_message_and_wait_for_completion

QA_API_BASE = "https://gateway.qa.unique.app/public/chat-gen2"
QA_USER_ID = "353194960666759723"
QA_COMPANY_ID = "225319369280852798"
QA_APP_ID = "app_le7m7o2w3zurin746dpx88ro"
QA_ASSISTANT_ID = "assistant_a9csiq8hbd10xnojpqlk6980"
KEYCHAIN_SERVICE = "unique-qa-public-api"
PROJECT_ROOT = Path(__file__).resolve().parents[4]
WORKBOOK_PATH = PROJECT_ROOT / "data" / "risk_database.xlsx"
CONNECTION_ERROR_MARKERS = (
    "mcp server not found",
    "session expired",
    "reconnect to continue",
)


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


def canonical_number(value: object) -> str:
    return format(float(value), "g")


def build_verification() -> tuple[str, tuple[str, ...], str]:
    pnl_daily = pd.read_excel(WORKBOOK_PATH, sheet_name="pnl_daily")
    dates = pd.to_datetime(pnl_daily["date"], errors="raise")
    latest_date = dates.max().strftime("%Y-%m-%d")
    latest_rows = pnl_daily.loc[
        dates == dates.max(),
        ["fund_id", "net_pnl_mm", "cum_ytd_pnl_mm"],
    ]
    expected_values = [latest_date]
    for row in latest_rows.itertuples(index=False):
        expected_values.extend(
            (
                str(row.fund_id),
                canonical_number(row.net_pnl_mm),
                canonical_number(row.cum_ytd_pnl_mm),
            )
        )
    prompt = f"""Call the connected Risk DB MCP query_data tool. Do not answer from memory.

Use these exact arguments:
- sheet_name: pnl_daily
- filters: {{"date": "{latest_date}"}}
- columns: ["fund_id", "date", "net_pnl_mm", "cum_ytd_pnl_mm"]
- limit: 10

Return the tool result and explicitly state whether matching rows were found."""
    return prompt, tuple(expected_values), latest_date


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
    prompt, expected_values, latest_date = build_verification()
    app_id = os.getenv("UNIQUE_APP_ID", QA_APP_ID)
    unique_sdk.api_base = os.getenv("UNIQUE_API_BASE", QA_API_BASE)
    unique_sdk.app_id = app_id
    unique_sdk.api_key = read_api_key(app_id)

    response = await send_message_and_wait_for_completion(
        user_id=os.getenv("UNIQUE_USER_ID", QA_USER_ID),
        company_id=os.getenv("UNIQUE_COMPANY_ID", QA_COMPANY_ID),
        assistant_id=os.getenv("UNIQUE_ASSISTANT_ID", QA_ASSISTANT_ID),
        text=prompt,
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
        value for value in expected_values if value not in normalized_answer
    ]
    if missing_values:
        print(
            "Verification failed: response is missing expected updated values: "
            + ", ".join(missing_values),
            file=sys.stderr,
        )
        return 1

    print(f"Verification passed: QA returned the {latest_date} Risk DB data.")
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(verify_qa_space(args.observe, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
