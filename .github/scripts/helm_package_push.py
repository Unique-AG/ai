#!/usr/bin/env python3
"""Package and push a dedicated Helm chart to one or more OCI registries.

This is the Python counterpart to the Deno ``helm-package-push.ts`` used in
the ``connectors`` repo. It runs ``helm dependency update`` → ``helm package``
→ ``helm push`` and is idempotent: a chart version that already exists in a
registry is skipped rather than re-pushed.

Two version modes
==================
* **Stable** (release event): the chart's ``Chart.yaml`` / ``values.yaml``
  have already been bumped by release-please at the ``# x-release-please-version``
  markers. Run without ``--version`` and the chart is packaged exactly as
  checked out.
* **Dev / rc** (push to ``main`` / promotion): the chart sits at the ``0.0.0``
  placeholder because release-please only bumps on stable. Pass the resolved
  PyPI version via ``--version`` and this script stamps it into the marked
  lines before packaging.

PyPI vs SemVer
==============
PyPI pre-release versions (PEP 440: ``2026.24.0.dev11``, ``2026.24.0rc1``) are
not valid SemVer-2, which Helm requires for ``Chart.yaml`` ``version``. So when
``--version`` is given, the value is written in two forms:

* ``Chart.yaml`` ``version`` → SemVer-2 (``2026.24.0-dev.11``, ``2026.24.0-rc.1``)
* ``Chart.yaml`` ``appVersion`` and ``values.yaml`` ``image.tag`` → the raw PyPI
  string, so the chart points at the container tag ``cd-containerize`` already
  pushed.

Example
=======
    python3 .github/scripts/helm_package_push.py \\
        --chart connectors/unique_search_proxy/deploy/helm-chart \\
        --registry oci://ghcr.io/unique-ag/ai/helm \\
        --version 2026.24.0.dev11 \\
        --destination /tmp
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Lines carrying this marker are the ones release-please rewrites on stable.
# We target the same markers so the dev/rc stamp stays in lockstep with the
# stable bump and never touches unrelated keys.
RELEASE_PLEASE_MARKER = "# x-release-please-version"

# PEP 440 pre-release segment → SemVer-2 pre-release label.
_PEP440_LABELS = {"dev": "dev", "rc": "rc", "a": "alpha", "b": "beta"}

# 2026.24.0 / 2026.24.0.dev11 / 2026.24.0rc1 / 2026.24.0a1 ...
_PEP440_RE = re.compile(
    r"^(?P<base>\d+\.\d+\.\d+)"
    r"(?:\.?(?P<label>dev|rc|a|b|alpha|beta)\.?(?P<num>\d+))?$"
)


class CommandError(RuntimeError):
    """A subprocess returned a non-zero exit code."""


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output; raise CommandError on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise CommandError(
            f"`{' '.join(cmd)}` failed ({result.returncode}):\n{result.stderr.strip()}"
        )
    return result


def pep440_to_semver(version: str) -> str:
    """Translate a PEP 440 version to a SemVer-2 chart version.

    Args:
        version: A PEP 440 version such as ``2026.24.0`` or ``2026.24.0.dev11``.

    Returns:
        The SemVer-2 equivalent (``2026.24.0`` or ``2026.24.0-dev.11``).

    Raises:
        ValueError: If ``version`` is not a recognised X.Y.Z[pre] form.
    """
    match = _PEP440_RE.match(version.strip())
    if not match:
        raise ValueError(
            f"Cannot convert {version!r} to SemVer-2: expected X.Y.Z with an "
            "optional dev/rc/a/b pre-release segment."
        )
    base = match.group("base")
    label = match.group("label")
    if not label:
        return base
    return f"{base}-{_PEP440_LABELS[label]}.{match.group('num')}"


def _stamp_marked_line(line: str, chart_version: str, raw_version: str) -> str:
    """Rewrite a single ``# x-release-please-version`` line in place.

    ``version:`` gets the SemVer chart version; ``appVersion:`` and ``tag:``
    get the raw PyPI version. Indentation and the trailing marker comment are
    preserved.
    """
    key_match = re.match(r"^(\s*)([A-Za-z]+):", line)
    if not key_match:
        return line
    indent, key = key_match.group(1), key_match.group(2)
    value = chart_version if key == "version" else raw_version
    return f'{indent}{key}: "{value}" {RELEASE_PLEASE_MARKER}\n'


def stamp_version(chart_dir: Path, raw_version: str) -> str:
    """Stamp the resolved version into the chart's marked lines.

    Rewrites every line carrying ``RELEASE_PLEASE_MARKER`` in ``Chart.yaml`` and
    ``values.yaml``: ``version`` → SemVer, ``appVersion`` / ``image.tag`` → raw.

    Args:
        chart_dir: Path to the chart directory.
        raw_version: Raw PyPI version (e.g. ``2026.24.0.dev11``).

    Returns:
        The SemVer chart version that was written to ``Chart.yaml``.
    """
    chart_version = pep440_to_semver(raw_version)
    for filename in ("Chart.yaml", "values.yaml"):
        path = chart_dir / filename
        if not path.exists():
            continue
        lines = path.read_text().splitlines(keepends=True)
        updated = [
            _stamp_marked_line(line, chart_version, raw_version)
            if RELEASE_PLEASE_MARKER in line
            else line
            for line in lines
        ]
        path.write_text("".join(updated))
    return chart_version


def read_chart_metadata(chart_dir: Path) -> tuple[str, str]:
    """Read the chart ``name`` and ``version`` from ``Chart.yaml``."""
    chart_yaml = (chart_dir / "Chart.yaml").read_text()
    name = re.search(r"^name:\s*([^#\n]+)", chart_yaml, re.MULTILINE)
    version = re.search(r"^version:\s*\"?([^\"#\n]+)", chart_yaml, re.MULTILINE)
    if not name:
        raise ValueError(f"Could not find chart name in {chart_dir / 'Chart.yaml'}")
    if not version:
        raise ValueError(f"Could not find chart version in {chart_dir / 'Chart.yaml'}")
    return name.group(1).strip(), version.group(1).strip()


def chart_exists(registry: str, name: str, version: str) -> bool:
    """Return True if ``name:version`` already exists in ``registry``."""
    try:
        run(["helm", "show", "chart", f"{registry}/{name}", "--version", version])
        return True
    except CommandError:
        return False


def render_helm_docs(chart_dir: Path) -> None:
    """Regenerate README.md so version badges match the stamped chart metadata."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "render-helm-docs.sh"
    if not script.is_file():
        raise ValueError(f"render-helm-docs.sh not found at {script}")
    run(["bash", str(script), str(chart_dir)])


def package_chart(chart_dir: Path, destination: Path) -> Path:
    """Resolve dependencies and package the chart, returning the ``.tgz`` path."""
    render_helm_docs(chart_dir)
    run(["helm", "dependency", "update", str(chart_dir)])
    result = run(["helm", "package", str(chart_dir), "--destination", str(destination)])
    match = re.search(r"saved it to:\s*(.+\.tgz)", result.stdout)
    if not match:
        raise ValueError(f"Could not find packaged chart path in:\n{result.stdout}")
    return Path(match.group(1).strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package and push a Helm chart to OCI registries."
    )
    parser.add_argument(
        "-c", "--chart", required=True, type=Path, help="Path to the chart directory."
    )
    parser.add_argument(
        "-r",
        "--registry",
        required=True,
        action="append",
        dest="registries",
        help="OCI registry, e.g. oci://ghcr.io/unique-ag/ai/helm (repeatable).",
    )
    parser.add_argument(
        "-d",
        "--destination",
        type=Path,
        default=Path("."),
        help="Directory for the packaged .tgz (default: current directory).",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Raw PyPI version to stamp (dev/rc). Omit on stable to package "
        "the chart as checked out.",
    )
    args = parser.parse_args()

    chart_dir: Path = args.chart
    if not (chart_dir / "Chart.yaml").exists():
        print(f"ERROR: no Chart.yaml under {chart_dir}", file=sys.stderr)
        return 1

    if args.version:
        chart_version = stamp_version(chart_dir, args.version)
        print(f"Stamped version: {args.version} (chart version {chart_version})")

    name, version = read_chart_metadata(chart_dir)
    print(f"Chart:      {name}")
    print(f"Version:    {version}")
    print(f"Registries: {', '.join(args.registries)}")

    args.destination.mkdir(parents=True, exist_ok=True)
    chart_package: Path | None = None

    for registry in args.registries:
        print(f"\n-> Processing registry: {registry}")
        if chart_exists(registry, name, version):
            print(f"   chart {name}:{version} already exists, skipping.")
            continue
        if chart_package is None:
            chart_package = package_chart(chart_dir, args.destination)
            print(f"   packaged: {chart_package.name}")
        run(["helm", "push", str(chart_package), registry])
        print(f"   pushed to {registry}")

    if chart_package is not None:
        chart_package.unlink(missing_ok=True)

    print("\nDone")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (CommandError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
