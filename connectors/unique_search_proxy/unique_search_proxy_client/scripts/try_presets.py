#!/usr/bin/env python3
"""Fire curated search/crawl presets against a running proxy and print payloads."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx
from unique_search_proxy_core.context import LOCAL_REQUEST_CONTEXT

from unique_search_proxy_client.web.presets import (
    PresetDefinition,
    PresetKind,
    get_preset,
    list_presets,
)

DEFAULT_BASE_URL = "http://localhost:2349"


def _pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _endpoint_for_kind(kind: PresetKind) -> str:
    if kind == "search":
        return "/v1/search"
    return "/v1/crawl"


def _result_count(body: dict[str, Any], kind: PresetKind) -> str:
    if kind == "search":
        curated = body.get("curated")
        if isinstance(curated, list):
            return f"results={len(curated)}"
        return "results=?"
    results = body.get("results")
    if isinstance(results, list):
        return f"urls={len(results)}"
    return "urls=?"


def _error_code(body: dict[str, Any]) -> str | None:
    error = body.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, str):
            return code
    return None


def _run_preset(
    client: httpx.Client,
    *,
    base_url: str,
    preset: PresetDefinition,
) -> tuple[int, float, dict[str, Any]]:
    payload = preset.build_payload()
    path = _endpoint_for_kind(preset.kind)
    started = time.perf_counter()
    response = client.post(
        f"{base_url.rstrip('/')}{path}",
        json=payload,
        headers=LOCAL_REQUEST_CONTEXT.to_headers(),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"raw": response.text}
    return response.status_code, elapsed_ms, body


def _print_run(
    *,
    preset: PresetDefinition,
    status_code: int,
    elapsed_ms: float,
    body: dict[str, Any],
) -> None:
    payload = preset.build_payload()
    print(f"\n=== {preset.id} ({preset.kind}) ===")
    print("--- request ---")
    print(_pretty_json(payload))
    print("--- response ---")
    print(_pretty_json(body))
    error_code = _error_code(body)
    if error_code is not None:
        detail = f"code={error_code}"
    else:
        detail = _result_count(body, preset.kind)
    print(f"--- summary --- status={status_code} {detail} latency_ms={elapsed_ms:.0f}")


def cmd_list(args: argparse.Namespace) -> int:
    presets = list_presets(kind=args.kind)
    for preset in presets:
        print(f"{preset.id:24} {preset.kind:6} {preset.summary}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    try:
        preset = get_preset(args.preset_id)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    with httpx.Client(timeout=args.timeout) as client:
        status_code, elapsed_ms, body = _run_preset(
            client,
            base_url=args.base_url,
            preset=preset,
        )
    _print_run(
        preset=preset,
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        body=body,
    )
    if args.strict and status_code >= 400:
        return 1
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    presets = list_presets(kind=args.kind)
    if not presets:
        print("No presets matched the filter.", file=sys.stderr)
        return 1

    exit_code = 0
    with httpx.Client(timeout=args.timeout) as client:
        for preset in presets:
            status_code, elapsed_ms, body = _run_preset(
                client,
                base_url=args.base_url,
                preset=preset,
            )
            _print_run(
                preset=preset,
                status_code=status_code,
                elapsed_ms=elapsed_ms,
                body=body,
            )
            if args.strict and status_code >= 400:
                exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run curated proxy payloads and inspect request/response JSON.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Proxy base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="HTTP client timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 when any response status is not 2xx",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available presets")
    list_parser.add_argument(
        "--kind",
        choices=("search", "crawl"),
        default=None,
        help="Filter by preset kind",
    )
    list_parser.set_defaults(func=cmd_list)

    run_parser = subparsers.add_parser("run", help="Run one preset by id")
    run_parser.add_argument("preset_id", help="Preset id (see `list`)")
    run_parser.set_defaults(func=cmd_run)

    run_all_parser = subparsers.add_parser(
        "run-all",
        help="Run every preset (optionally filtered by kind)",
    )
    run_all_parser.add_argument(
        "--kind",
        choices=("search", "crawl"),
        default=None,
        help="Only run search or crawl presets",
    )
    run_all_parser.set_defaults(func=cmd_run_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
