#!/usr/bin/env python3
"""Resolve dev versions and cross-package dep pins for a dev publish run.

For every publishable AI package we query PyPI once to learn:

  * The highest pre-release (``YYYY.WW.0.devN``) already published in the
    current CalVer cycle, if any.
  * The highest non-pre-release ever published (the "last stable"), which
    is our fallback when the current cycle has no dev wheels yet.

From that we compute two things:

  * ``new_versions``: for every package scheduled to publish in this
    push, the next ``YYYY.WW.0.devN`` (per-package contiguous counter:
    ``dev0, dev1, dev2, ...`` within a cycle, no gaps).

  * ``dep_pins``: for every publishable AI package, the PEP 440 spec
    suffix that should be stamped into any cross-package AI dep that
    references it. Three cases:
      - package is a sibling in this push  -> ``==<new_version>``
      - cycle already has a dev wheel      -> ``>=<highest-dev-in-cycle>``
      - otherwise                          -> ``>=<last-stable>``

The map is keyed by PEP 503 normalized project name so the downstream
``rewrite-pyproject-for-dev.py`` can apply it regardless of whether the
requirement string spells the name with ``-``, ``_`` or ``.``.

Inputs (CLI):
    --cycle YYYY.WW                  Target CalVer cycle.
    --selected-ids '["toolkit",...]' JSON array of matrix ids to publish.
    --output-dir DIR                 Where new_versions.json and
                                     dep_pins.json will be written.
    --package-config FILE            Path to package_configuration.json.
                                     Defaults to the canonical location.
    --pypi-base-url URL              PyPI JSON API base (tests override).

In practice the workflow provides ``--cycle`` and ``--selected-ids``;
everything else has sensible defaults.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACKAGE_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "actions"
    / "get-packages-matrix"
    / "package_configuration.json"
)

DEFAULT_PYPI_BASE_URL = "https://pypi.org/pypi"

_CYCLE_RE = re.compile(r"^\d{4}\.\d{2}$")


def normalize(name: str) -> str:
    # PEP 503 normalization.
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Publishable:
    id: str
    pypi_name: str


@dataclass(frozen=True)
class PyPiState:
    # Highest dev counter already published in the target cycle, or None.
    max_dev_in_cycle: int | None
    # Highest stable (non-pre) version, or None for brand-new packages.
    last_stable: str | None


def load_publishable(config_path: Path) -> list[Publishable]:
    raw = json.loads(config_path.read_text())
    out: list[Publishable] = []
    for entry in raw:
        if entry.get("publish_skip"):
            continue
        pypi_name = entry.get("pypi_name")
        if not pypi_name:
            continue
        out.append(Publishable(id=entry["id"], pypi_name=pypi_name))
    return out


# "YYYY.WW.0.devN" — we only care about the cycle prefix + the dev counter.
_DEV_IN_CYCLE_RE = re.compile(r"^(?P<cycle>\d{4}\.\d{2})\.0\.dev(?P<n>\d+)$")
# Stable release: any dotted numeric version with no pre-release segment.
# This deliberately includes pre-CalVer legacy versions like "0.3.0" and
# "1.69.6" so the last-stable fallback works for packages that haven't
# been migrated to CalVer yet.
_STABLE_RE = re.compile(r"^\d+(\.\d+)*$")


def classify_versions(versions: list[str], cycle: str) -> PyPiState:
    max_dev: int | None = None
    last_stable_tuple: tuple[int, ...] | None = None
    last_stable_str: str | None = None
    for v in versions:
        m = _DEV_IN_CYCLE_RE.match(v)
        if m and m.group("cycle") == cycle:
            n = int(m.group("n"))
            if max_dev is None or n > max_dev:
                max_dev = n
            continue
        if _STABLE_RE.match(v):
            parts = tuple(int(x) for x in v.split("."))
            if last_stable_tuple is None or parts > last_stable_tuple:
                last_stable_tuple = parts
                last_stable_str = v
    return PyPiState(max_dev_in_cycle=max_dev, last_stable=last_stable_str)


def fetch_pypi_versions(
    pypi_name: str,
    base_url: str,
    *,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    opener: urllib.request.OpenerDirector | None = None,
) -> list[str]:
    """Fetch published version strings from PyPI's JSON API.

    Returns [] when the package has never been published (404). Any other
    network failure is retried ``retries`` times before bubbling up.
    """
    url = f"{base_url}/{pypi_name}/json"
    _open = opener.open if opener is not None else urllib.request.urlopen
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with _open(url, timeout=15) as resp:  # type: ignore[misc]
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return []
            last_exc = exc
        except Exception as exc:  # noqa: BLE001 - network is noisy
            last_exc = exc
        else:
            return list((payload.get("releases") or {}).keys())
        if attempt < retries:
            time.sleep(backoff_seconds * attempt)
    assert last_exc is not None
    raise last_exc


def resolve(
    *,
    cycle: str,
    selected_ids: list[str],
    publishable: list[Publishable],
    pypi_base_url: str,
    fetcher=fetch_pypi_versions,
) -> tuple[dict[str, str], dict[str, str]]:
    if not _CYCLE_RE.match(cycle):
        raise SystemExit(f"invalid cycle: {cycle!r}")

    known_ids = {p.id for p in publishable}
    unknown = [sid for sid in selected_ids if sid not in known_ids]
    if unknown:
        raise SystemExit(
            f"selected ids reference packages not in publishable config: {unknown}"
        )

    selected_set = set(selected_ids)

    state_by_id: dict[str, PyPiState] = {}
    for pkg in publishable:
        versions = fetcher(pkg.pypi_name, pypi_base_url)
        state_by_id[pkg.id] = classify_versions(versions, cycle)

    new_versions: dict[str, str] = {}
    for pkg in publishable:
        if pkg.id not in selected_set:
            continue
        state = state_by_id[pkg.id]
        next_n = 0 if state.max_dev_in_cycle is None else state.max_dev_in_cycle + 1
        new_versions[pkg.id] = f"{cycle}.0.dev{next_n}"

    dep_pins: dict[str, str] = {}
    for pkg in publishable:
        normalized = normalize(pkg.pypi_name)
        if pkg.id in selected_set:
            dep_pins[normalized] = f"=={new_versions[pkg.id]}"
            continue
        state = state_by_id[pkg.id]
        if state.max_dev_in_cycle is not None:
            dep_pins[normalized] = f">={cycle}.0.dev{state.max_dev_in_cycle}"
        elif state.last_stable is not None:
            dep_pins[normalized] = f">={state.last_stable}"
        else:
            # Brand-new package with no wheel anywhere: the only honest
            # thing we can say is ">=0".
            dep_pins[normalized] = ">=0"

    return new_versions, dep_pins


def _render_summary(
    *,
    cycle: str,
    selected_ids: list[str],
    publishable: list[Publishable],
    new_versions: dict[str, str],
    dep_pins: dict[str, str],
) -> str:
    lines = [
        "### Dev publish — version resolution",
        "",
        f"- Cycle: `{cycle}`",
        f"- Selected packages ({len(selected_ids)}): "
        f"`{', '.join(selected_ids) or '(none)'}`",
        "",
        "| package | new version |",
        "| --- | --- |",
    ]
    for pkg in publishable:
        if pkg.id in new_versions:
            lines.append(f"| `{pkg.id}` | `{new_versions[pkg.id]}` |")
    lines.extend(
        [
            "",
            "| dep | pinned to |",
            "| --- | --- |",
        ]
    )
    for name in sorted(dep_pins):
        lines.append(f"| `{name}` | `{dep_pins[name]}` |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--selected-ids", required=True, help="JSON array")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--package-config", default=str(DEFAULT_PACKAGE_CONFIG), type=Path
    )
    parser.add_argument("--pypi-base-url", default=DEFAULT_PYPI_BASE_URL)
    args = parser.parse_args(argv)

    selected_ids = json.loads(args.selected_ids)
    if not isinstance(selected_ids, list) or not all(
        isinstance(s, str) for s in selected_ids
    ):
        raise SystemExit("--selected-ids must be a JSON array of strings")

    publishable = load_publishable(Path(args.package_config))

    new_versions, dep_pins = resolve(
        cycle=args.cycle,
        selected_ids=selected_ids,
        publishable=publishable,
        pypi_base_url=args.pypi_base_url,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "new_versions.json").write_text(json.dumps(new_versions, indent=2))
    (out_dir / "dep_pins.json").write_text(json.dumps(dep_pins, indent=2))

    print(
        _render_summary(
            cycle=args.cycle,
            selected_ids=selected_ids,
            publishable=publishable,
            new_versions=new_versions,
            dep_pins=dep_pins,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
