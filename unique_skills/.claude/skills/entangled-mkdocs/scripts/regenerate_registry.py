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


def build_registry(docs_dir: pathlib.Path) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    for md in sorted(docs_dir.rglob("*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            if not re.match(r"^`{3,}", line):
                continue
            id_m = re.search(r"#([\w-]+)", line)
            file_m = re.search(r"file=([^\s}]+)", line)
            if id_m:
                blocks.setdefault("#" + id_m.group(1), []).append(str(md))
            if file_m:
                blocks.setdefault("file=" + file_m.group(1), []).append(str(md))
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

    duplicates = {k: v for k, v in blocks.items() if len(v) > 1}
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
