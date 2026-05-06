# Benchmarking run utility

End-to-end flow for benchmarking xlsx files: **upload from disk → wait until processing finishes → optionally save the result workbook** in one async call. Polling defaults match long-running jobs (5 s between checks, 10 minute cap), similar in spirit to [Chat in Space](chat_in_space.md) helpers.

## Function

??? example "`unique_sdk.utils.benchmarking_run.run_benchmarking_from_file`"

    **Parameters:**

    - `user_id`, `company_id` (required)
    - `path_to_file` (required) — path to your `.xlsx`
    - `displayed_filename` (optional) — name used for the upload (default: file basename)
    - `force` (optional) — pass through to the upload call when the API supports it
    - `poll_interval` (optional, default `5.0`) — seconds between status polls
    - `max_wait` (optional, default `600.0`) — total seconds before a `TimeoutError` is raised
    - `save_result_to` (optional) — if set, copies the finished workbook from its temp download path to this path. The download is skipped when every item in the benchmark errored (`done == 0`); in that case `result_path` will not appear in the returned dict.

    **Returns:** A dict with `upload` and `status`; includes `result_path` when `save_result_to` was set **and** at least one item completed successfully.

    **Example:**

    ```python
    import asyncio
    from unique_sdk.utils.benchmarking_run import run_benchmarking_from_file

    async def main():
        result = await run_benchmarking_from_file(
            user_id=user_id,
            company_id=company_id,
            path_to_file="./benchmark.xlsx",
            save_result_to="./benchmark_result.xlsx",
        )
        print(result["status"])

    asyncio.run(main())
    ```

## Adjusting the polling behaviour

The two parameters that control polling are `poll_interval` and `max_wait`:

| Parameter | Default | Effect |
|---|---|---|
| `poll_interval` | `5.0` | Seconds to sleep between consecutive `get_status` calls. |
| `max_wait` | `600.0` | Upper bound (in seconds) on total polling time. The function raises `TimeoutError` once this limit is exceeded. |

The number of attempts is derived automatically: `max(1, int(max_wait // poll_interval))`.

**Quick benchmarks (small files, expected < 1 min)** — poll more frequently with a shorter timeout:

```python
result = await run_benchmarking_from_file(
    user_id=user_id,
    company_id=company_id,
    path_to_file="./small_benchmark.xlsx",
    poll_interval=2.0,   # check every 2 s
    max_wait=120.0,      # give up after 2 min
)
```

**Large benchmarks (many rows, expected 10–30 min)** — poll less often to reduce API calls, with a generous timeout:

```python
result = await run_benchmarking_from_file(
    user_id=user_id,
    company_id=company_id,
    path_to_file="./large_benchmark.xlsx",
    poll_interval=15.0,  # check every 15 s
    max_wait=1800.0,     # give up after 30 min
)
```

**CI / automated pipelines** — keep `max_wait` tight so a stuck job fails fast:

```python
result = await run_benchmarking_from_file(
    user_id=user_id,
    company_id=company_id,
    path_to_file="./benchmark.xlsx",
    poll_interval=5.0,
    max_wait=300.0,      # 5 min hard limit
)
```

!!! note
    If polling times out, you still get a `TimeoutError` with the last observed status embedded in the message. The benchmark may still be running on the server — call `Benchmarking.get_status()` later to check.
