# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Create a changie-compatible fragment in .changelog/unreleased/ without installing changie."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
config = yaml.safe_load((ROOT / ".changie.yaml").read_text())
packages = [
    p["component"]
    for p in json.loads((ROOT / "release-please-config.json").read_text())[
        "packages"
    ].values()
]
audiences = next(c["enumOptions"] for c in config["custom"] if c["key"] == "Audience")


def csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--kind", required=True, choices=[k["label"] for k in config["kinds"]]
)
parser.add_argument("--component", required=True, choices=config["components"])
parser.add_argument("--audience", required=True, choices=audiences)
parser.add_argument(
    "--package", required=True, help=f"comma-separated, from: {', '.join(packages)}"
)
parser.add_argument("--ticket", default="", help="comma-separated UN-12345 ids")
parser.add_argument("--body", required=True)
args = parser.parse_args()

if bad := [p for p in csv(args.package) if p not in packages]:
    sys.exit(f"unknown package(s): {', '.join(bad)}")
if bad := [t for t in csv(args.ticket) if not re.fullmatch(r"UN-\d+", t)]:
    sys.exit(f"invalid ticket(s): {', '.join(bad)}")

now = datetime.now().astimezone()
custom = {"Audience": args.audience, "Package": ", ".join(csv(args.package))}
if args.ticket:
    custom["Ticket"] = ", ".join(csv(args.ticket))
slug = args.component.replace(" ", "-").replace("/", "-").lower()
path = (
    ROOT
    / ".changelog"
    / "unreleased"
    / f"{args.kind.lower()}-{slug}-{now:%Y%m%d-%H%M%S}.yaml"
)
fragment = {
    "component": args.component,
    "kind": args.kind,
    "body": args.body.strip(),
    "time": now.isoformat(),
    "custom": custom,
}
with path.open("x") as f:
    f.write(yaml.safe_dump(fragment, sort_keys=False, allow_unicode=True))
print(path.relative_to(ROOT))
