from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


async def poll_batch_scrape(
    client: httpx.AsyncClient,
    *,
    status_url: str,
    api_key: str,
    deadline: float,
    poll_interval: float = 2.0,
) -> dict[str, Any]:
    """Poll Firecrawl ``GET /v2/batch/scrape/{id}`` until terminal or deadline."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Firecrawl batch scrape polling timed out")

        response = await client.get(
            status_url,
            headers=headers,
            timeout=max(deadline - time.monotonic(), 1.0),
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Firecrawl batch scrape status returned non-object JSON")

        status = payload.get("status")
        if isinstance(status, str) and status in _TERMINAL_STATUSES:
            return payload

        await asyncio.sleep(poll_interval)
