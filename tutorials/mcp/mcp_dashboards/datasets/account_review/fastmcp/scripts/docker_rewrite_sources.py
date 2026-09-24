"""Rewrite uv path/workspace sources for the container image layout under /deps."""

from __future__ import annotations

import re
from pathlib import Path

SOURCES_BLOCK_RE = re.compile(r"\n\[tool\.uv\.sources\]\n(?:.*\n)*?(?=\n\[|\Z)")


def _replace_sources(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = SOURCES_BLOCK_RE.sub("\n", text)
    path.write_text(text.rstrip() + "\n\n" + block.strip() + "\n", encoding="utf-8")


def main() -> None:
    _replace_sources(
        Path("pyproject.toml"),
        """
[tool.uv.sources]
unique-mcp = { path = "/deps/unique_mcp", editable = true }
unique-toolkit = { path = "/deps/unique_toolkit", editable = true }
unique-sdk = { path = "/deps/unique_sdk", editable = true }
""",
    )
    _replace_sources(
        Path("/deps/unique_mcp/pyproject.toml"),
        """
[tool.uv.sources]
unique-toolkit = { path = "/deps/unique_toolkit", editable = true }
""",
    )
    _replace_sources(
        Path("/deps/unique_toolkit/pyproject.toml"),
        """
[tool.uv.sources]
unique-sdk = { path = "/deps/unique_sdk", editable = true }
""",
    )
    print("Rewrote uv.sources for /deps layout")


if __name__ == "__main__":
    main()
