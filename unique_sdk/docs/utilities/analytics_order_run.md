# Analytics order run utility

End-to-end flow for analytics reports: **create an order → poll until it reaches a terminal state → optionally save the CSV** in one async call. Polling defaults suit long-running jobs (5 s between checks, 10 minute cap), similar in spirit to the [Benchmarking run utility](benchmarking_run.md).

## Function

??? example "`unique_sdk.utils.analytics_order_run.run_analytics_order`"

    **Parameters:**

    - `user_id`, `company_id` (required)
    - `type` (required) — a valid analytics [type string](../api_resources/analytics_order.md#analytics-types) (e.g. `"CHAT_INTERACTION"`), matching `AnalyticsOrder.AnalyticsTypeLiteral` and `AnalyticsOrder.ANALYTICS_TYPE_VALUES` (see [API](../api_resources/analytics_order.md#analytics-type-literal))
    - `start_date` (required) — ISO 8601 date string (e.g. `"2024-01-01"`)
    - `end_date` (required) — ISO 8601 date string (e.g. `"2024-12-31"`)
    - `assistant_id` (optional) — filter the report to a specific assistant
    - `poll_interval` (optional, default `5.0`) — seconds between status polls
    - `max_wait` (optional, default `600.0`) — total seconds before a `TimeoutError` is raised
    - `save_csv_to` (optional) — if set, writes the finished CSV to this path once the order reaches `DONE`. The download is skipped when the order ends in `ERROR`; in that case `csv_path` will not appear in the returned dict.

    **Returns:** A dict with `order` (the final `AnalyticsOrder` object); includes `csv_path` when `save_csv_to` was set **and** the order succeeded.

    **Example:**

    ```python
    import asyncio
    from unique_sdk.utils.analytics_order_run import run_analytics_order

    async def main():
        result = await run_analytics_order(
            user_id=user_id,
            company_id=company_id,
            type="CHAT_INTERACTION",
            start_date="2024-01-01",
            end_date="2024-12-31",
            save_csv_to="./report.csv",
        )
        print(result["order"]["state"])   # "DONE"
        print(result.get("csv_path"))     # "./report.csv"

    asyncio.run(main())
    ```

## Adjusting the polling behaviour

The two parameters that control polling are `poll_interval` and `max_wait`:

| Parameter | Default | Effect |
|---|---|---|
| `poll_interval` | `5.0` | Seconds to sleep between consecutive `retrieve` calls. |
| `max_wait` | `600.0` | Upper bound (in seconds) on total polling time. The function raises `TimeoutError` once this limit is exceeded. |

The number of attempts is derived automatically: `max(1, int(max_wait // poll_interval))`.

**Small date ranges (expected < 1 min)** — poll more frequently with a shorter timeout:

```python
result = await run_analytics_order(
    user_id=user_id,
    company_id=company_id,
    type="CHAT_INTERACTION",
    start_date="2024-12-01",
    end_date="2024-12-31",
    poll_interval=2.0,   # check every 2 s
    max_wait=120.0,      # give up after 2 min
)
```

**Large date ranges (expected 10–30 min)** — poll less often to reduce API calls:

```python
result = await run_analytics_order(
    user_id=user_id,
    company_id=company_id,
    type="CHAT_INTERACTION",
    start_date="2023-01-01",
    end_date="2024-12-31",
    poll_interval=15.0,   # check every 15 s
    max_wait=1800.0,      # give up after 30 min
    save_csv_to="./full_report.csv",
)
```

**CI / automated pipelines** — keep `max_wait` tight so a stuck job fails fast:

```python
result = await run_analytics_order(
    user_id=user_id,
    company_id=company_id,
    type="CHAT_INTERACTION",
    start_date="2024-01-01",
    end_date="2024-12-31",
    poll_interval=5.0,
    max_wait=300.0,      # 5 min hard limit
)
```

!!! note
    If polling times out, you get a `TimeoutError` with the last observed order state embedded in the message. The order may still be running on the server — call `AnalyticsOrder.retrieve()` later to check.

## Return Types

#### RunAnalyticsOrderResult {#runanalyticsorderresult}

??? note "The result dict returned by `run_analytics_order`"

    **Fields:**

    - `order` ([`AnalyticsOrder`](../api_resources/analytics_order.md#analyticsorder)) - The final order object after reaching a terminal state
    - `csv_path` (str, optional) - Absolute path to the saved CSV file. Only present when `save_csv_to` was set **and** the order reached `DONE` state.

## Related Resources

- [Analytics Order API](../api_resources/analytics_order.md) - Low-level create, list, retrieve, delete, and download methods
