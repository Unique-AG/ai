# Benchmarking run utility

End-to-end flow for benchmarking xlsx files: **upload from disk → wait until processing finishes → optionally save the result workbook** in one async call. Polling defaults match long-running jobs (5s between checks, 10 minute cap), similar in spirit to [Chat in Space](chat_in_space.md) helpers.

## Function

??? example "`unique_sdk.utils.benchmarking_run.run_benchmarking_from_file`"

    **Parameters:**

    - `user_id`, `company_id` (required)
    - `path_to_file` (required) — path to your `.xlsx`
    - `displayed_filename` (optional) — name used for the upload (default: file basename)
    - `force` (optional) — pass through to the upload call when the API supports it
    - `poll_interval` (optional, default `5.0`) — how often to re-check progress (seconds)
    - `max_wait` (optional, default `600.0`) — give up after this many seconds (`TimeoutError`)
    - `save_result_to` (optional) — if set, copies the finished workbook from its temp download path to this path

    **Returns:** A dict with `upload` and `status`; includes `result_path` when you passed `save_result_to`.

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
