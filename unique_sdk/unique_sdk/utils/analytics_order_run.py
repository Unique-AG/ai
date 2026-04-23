import asyncio
from pathlib import Path
from typing import Any

from unique_sdk.api_resources._analytics_order import AnalyticsOrder

_DONE_STATES = {"DONE", "ERROR"}


def _is_terminal(order: AnalyticsOrder) -> bool:
    return str(order.get("state", "")).upper() in _DONE_STATES


async def _poll_until_terminal(
    user_id: str,
    company_id: str,
    order_id: str,
    poll_interval: float,
    max_wait: float,
) -> AnalyticsOrder:
    max_attempts = max(1, int(max_wait // poll_interval))
    last: AnalyticsOrder | None = None
    for _ in range(max_attempts):
        last = await AnalyticsOrder.retrieve_async(user_id, company_id, order_id)
        if _is_terminal(last):
            return last
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        "Timed out waiting for analytics order %s to complete. Last state: %r"
        % (order_id, last.get("state") if last else None)
    )


async def run_analytics_order(
    user_id: str,
    company_id: str,
    type: str,
    start_date: str,
    end_date: str,
    *,
    assistant_id: str | None = None,
    poll_interval: float = 5.0,
    max_wait: float = 600.0,
    save_csv_to: str | None = None,
) -> dict[str, Any]:
    """
    Create an analytics order, poll until it finishes, and optionally save the CSV.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        type: The analytics type (e.g. ``"CHAT_ANALYTICS"``).
        start_date: Report start date in ISO 8601 format (e.g. ``"2024-01-01"``).
        end_date: Report end date in ISO 8601 format (e.g. ``"2024-12-31"``).
        assistant_id: Optional assistant ID to filter the report by.
        poll_interval: Seconds between status polls (default ``5.0``).
        max_wait: Maximum seconds to wait for completion (default ``600.0``).
        save_csv_to: If set, writes the downloaded CSV content to this path once
            the order reaches ``DONE`` state. The download is skipped when the
            order ends in ``ERROR``; in that case ``csv_path`` will not appear
            in the returned dict.

    Returns:
        A dict with ``order`` (the final :class:`AnalyticsOrder` object) and,
        when ``save_csv_to`` was set and the order succeeded, ``csv_path``.

    Raises:
        TimeoutError: If the order does not reach a terminal state within ``max_wait``.
    """
    create_kwargs: dict[str, Any] = {
        "type": type,
        "start_date": start_date,
        "end_date": end_date,
    }
    if assistant_id is not None:
        create_kwargs["assistant_id"] = assistant_id

    order = await AnalyticsOrder.create_async(user_id, company_id, **create_kwargs)
    order_id = str(order.get("id"))

    final_order = await _poll_until_terminal(
        user_id, company_id, order_id, poll_interval, max_wait
    )

    out: dict[str, Any] = {"order": final_order}

    if save_csv_to and str(final_order.get("state", "")).upper() == "DONE":
        csv_content = await AnalyticsOrder.download_async(user_id, company_id, order_id)
        dest = Path(save_csv_to)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(csv_content, encoding="utf-8")
        out["csv_path"] = str(dest)

    return out
