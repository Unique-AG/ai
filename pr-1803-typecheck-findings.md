# PR 1803 Typecheck Failure Findings

## Summary

PR [#1803](https://github.com/Unique-AG/ai/pull/1803) fails the CI Gatekeeper because the strict typecheck jobs for `unique_sdk` and `unique_toolkit` fail.

Tracking ticket: [UN-22137](https://unique-ch.atlassian.net/browse/UN-22137)

The failing diagnostics are:

- `unique_sdk/unique_sdk/utils/file_io.py`: `requests.get(..., headers=headers)` receives `dict[str, str | None]`.
- `unique_toolkit/unique_toolkit/content/functions.py`: `requests.get(..., headers=headers)` receives `dict[str, str | None]`.

`requests` now types `headers` as requiring non-`None` values. The local header dictionaries include `unique_sdk.app_id`, which is declared as `str | None`.

## Root Cause

The sync download helpers build headers directly from nullable SDK globals:

- `unique_sdk.app_id: str | None`
- `unique_sdk.api_key: str | None`

Because at least one header value can be `None`, basedpyright infers the whole dictionary as `dict[str, str | None]`. That is not assignable to the `requests.get` `headers` parameter.

The async toolkit helper already uses the safer pattern: build `raw_headers: dict[str, str | None]`, then filter out `None` values into `dict[str, str]` before calling the HTTP client.

## Where This Was Introduced

The underlying code paths are old, but the CI-visible regression was introduced by PR [#1771 feat: User Memory](https://github.com/Unique-AG/ai/pull/1771).

That PR updated `uv.lock`, including:

- `basedpyright` from `1.39.1` to `1.39.6`
- `pyright` from `1.1.408` to `1.1.410`
- `requests` from `2.33.1` to `2.34.2`

Those updated type definitions made the existing nullable header construction fail strict typechecking.

## Why It Was Not Caught Earlier

CI selects package checks from changed paths. PR #1771 changed `uv.lock` and package paths for `unique_orchestrator` and `unique_user_memory`, so the typecheck jobs that ran were:

- `types-orchestrator`
- `types-user_memory`

It did not run:

- `types-sdk`
- `types-toolkit`

The release PR #1803 updates many package `pyproject.toml` files, so the strict `unique_sdk` and `unique_toolkit` typecheck jobs run and expose the existing issue.

## Fix Direction

Use a consistent header construction helper or local pattern for sync code:

1. Build `raw_headers: dict[str, str | None]`.
2. Filter out `None` values.
3. Pass the resulting `dict[str, str]` to `requests.get`.

This preserves runtime behavior for optional SDK globals and satisfies the stricter `requests` header type.
