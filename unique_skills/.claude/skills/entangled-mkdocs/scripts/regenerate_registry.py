"""
Regenerate docs/entangled-registry.json from all Markdown files under docs/.

Usage:
    python scripts/regenerate_registry.py

Run from the project root (where mkdocs.yaml lives). Add to mkdocs.yaml:

    exclude_docs: |
      entangled-registry.json

Exit codes:
    0  registry written (or unchanged)
    1  duplicate block IDs or file= targets detected
"""

import json
import pathlib
import re
import sys

DOCS_DIR = pathlib.Path("docs")
REGISTRY_PATH = DOCS_DIR / "entangled-registry.json"


# Fence at line start (3+ backticks). Group 1 = backticks.
_FENCE_OPEN = re.compile(r"^(`{3,})")
# Closing fence: line is only backticks and optional whitespace.
_FENCE_CLOSE = re.compile(r"^(`{3,})\s*$")


def build_registry(docs_dir: pathlib.Path) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    for md in sorted(docs_dir.rglob("*.md")):
        fence_stack: list[int] = []  # backtick count of each open fence
        for line in md.read_text(encoding="utf-8").splitlines():
            close_m = _FENCE_CLOSE.match(line)
            if close_m:
                n = len(close_m.group(1))
                if fence_stack and fence_stack[-1] == n:
                    _ = fence_stack.pop()
                continue
            open_m = _FENCE_OPEN.match(line)
            if not open_m:
                continue
            n = len(open_m.group(1))
            if fence_stack:
                if fence_stack[-1] == n:
                    # Same backtick count: in Markdown a new fence closes the previous (no nesting).
                    _ = fence_stack.pop()
                else:
                    # Different count = truly nested (e.g. 3 inside 4-backtick doc example); do not register.
                    fence_stack.append(n)
                    continue
            # Top-level fence (or just closed same-count): register #id and file= for this block.
            id_m = re.search(r"#([\w-]+)", line)
            file_m = re.search(r"file=([^\s}]+)", line)
            if id_m:
                blocks.setdefault("#" + id_m.group(1), []).append(str(md))
            if file_m:
                blocks.setdefault("file=" + file_m.group(1), []).append(str(md))
            fence_stack.append(n)
    return blocks


def main() -> int:
    if not DOCS_DIR.exists():
        print(f"Error: docs directory not found at '{DOCS_DIR}'", file=sys.stderr)
        return 1

    blocks = build_registry(DOCS_DIR)

    REGISTRY_PATH.write_text(
        json.dumps(blocks, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Registry written: {len(blocks)} entries → {REGISTRY_PATH}")

    duplicates = {k: v for k, v in blocks.items() if len(set(v)) > 1}
    if duplicates:
        print(f"\nWARNING: {len(duplicates)} duplicate(s) found:", file=sys.stderr)
        for key, files in duplicates.items():
            print(f"  {key}", file=sys.stderr)
            for f in files:
                print(f"    {f}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
