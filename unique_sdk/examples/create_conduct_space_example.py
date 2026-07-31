#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "unique-toolkit>=2026.28.0",
#     "unique-sdk>=2026.28.0",
# ]
# ///
"""Create a Conduct space via the Space API (`uiType=UNIQUE_CONDUCT`).

Credentials are read from the current environment, or from an env file passed
with `--env-file`.

Example:
    uv run examples/create_conduct_space_example.py --env-file .qa.env
    uv run examples/create_conduct_space_example.py --env-file .qa.env --keep
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from unique_toolkit.app.unique_settings import UniqueSettings

from unique_sdk import Space

ASSISTANT_NAME = "__conduct_space_demo_safe_to_delete__"
MODULE_NAME = "SwappableIntelligence"


def load_unique_settings(env_file: Path | None) -> tuple[UniqueSettings, str, str]:
    if env_file is not None:
        settings = UniqueSettings.from_env(env_file=env_file)
        settings.init_sdk()
    else:
        settings = UniqueSettings.from_env_auto_with_sdk_init()

    return (
        settings,
        settings.authcontext.get_confidential_user_id(),
        settings.authcontext.get_confidential_company_id(),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Conduct (Swappable Intelligence) space."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional .env file to load before reading UNIQUE_* credentials.",
    )
    parser.add_argument(
        "--name",
        default=ASSISTANT_NAME,
        help="Space name (default: demo name that is safe to delete).",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Do not delete the space after creation.",
    )
    return parser.parse_args()


def build_module_configuration(project_name: str) -> dict[str, Any]:
    """Minimal module config accepted by SwappableIntelligence / Conduct.

    Full schema: monorepo ``SwappableIntelligenceConfig``
    (``python/assistants/bundles/core/.../swappable_intelligence/config.py``).
    An empty ``{}`` also works (server defaults apply).
    """
    return {
        "strategy": "claude_code",
        "space": {"projectName": project_name},
        "setup": {
            "customInstructions": "You are a helpful Conduct agent.",
        },
        "tools": [],
        "claude": {},
        "piAgent": {},
        "codex": {},
        "cursorSdk": {},
    }


def delete_existing_demo_spaces(user_id: str, company_id: str, name: str) -> None:
    spaces = Space.get_spaces(user_id, company_id, name=name, take=100)
    for space in spaces.get("data", []):
        if space.get("name") != name:
            continue
        Space.delete_space(user_id, company_id, space["id"])
        print(f"Deleted stale demo space: {space['id']}")


def main() -> None:
    args = parse_args()
    _, user_id, company_id = load_unique_settings(args.env_file)

    if args.name == ASSISTANT_NAME:
        delete_existing_demo_spaces(user_id, company_id, args.name)

    space = Space.create_space(
        user_id,
        company_id,
        name=args.name,
        uiType="UNIQUE_CONDUCT",
        fallbackModule=MODULE_NAME,
        modules=[
            {
                "name": MODULE_NAME,
                "weight": 500,
                "configuration": build_module_configuration(args.name),
            }
        ],
        chatUpload="ENABLED",
        explanation="Programmatically created Conduct space",
    )
    space_id = space["id"]
    print(f"Created Conduct space: {space_id}")
    print(f"Chat path: /space/{space_id}")
    print(f"Admin path: /swappable-intelligence-space/{space_id}")

    if not args.keep:
        Space.delete_space(user_id, company_id, space_id)
        print(f"Deleted space: {space_id}")
    else:
        print(
            "Kept space (--keep). Delete it from Admin or via Space.delete_space when done."
        )


if __name__ == "__main__":
    main()
