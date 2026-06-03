#!/usr/bin/env python3
"""Export OpenAPI from the FastAPI app and regenerate ``unique_search_proxy.sdk._generated``."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "openapi.json"
OUTPUT_PATH = ROOT / "unique_search_proxy" / "sdk" / "_generated"
CONFIG_PATH = ROOT / "scripts" / "openapi-client-config.yaml"


def export_openapi() -> None:
    from unique_search_proxy.web.app import create_app

    schema = create_app().openapi()
    OPENAPI_PATH.write_text(
        json.dumps(schema, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OPENAPI_PATH} ({len(schema.get('paths', {}))} paths)")


def generate_client() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "openapi_python_client",
            "generate",
            "--path",
            str(OPENAPI_PATH),
            "--output-path",
            str(OUTPUT_PATH),
            "--config",
            str(CONFIG_PATH),
            "--meta",
            "none",
            "--overwrite",
        ],
        check=True,
        cwd=ROOT,
    )
    print(f"Generated client at {OUTPUT_PATH}")


def main() -> None:
    export_openapi()
    generate_client()


if __name__ == "__main__":
    main()
