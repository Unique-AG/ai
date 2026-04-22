#!/usr/bin/env bash
set -euo pipefail

# Emits the subset of publishable packages whose sources changed between
# <base-sha> and <head-sha> as a GitHub Actions matrix JSON, e.g.
#   {"include":[{"id":"toolkit","dir":"unique_toolkit",...}]}
#
# Special cases — any of these yield the full publishable matrix:
#   * base is the null SHA (new branch / first push)
#   * base..head is unreachable (shallow clone / force-push); caller must
#     fetch enough history for the diff to work
#   * any "invalidator" path changed (publish pipeline itself, packages
#     JSON, rewrite script) — we want to exercise the new mechanism on
#     every wheel
#
# Changes that don't touch any package directory yield an empty matrix
# (`{"include":[]}`). Callers should skip the publish job in that case.
#
# Usage: detect-changed-packages.sh <base-sha> <head-sha>

BASE="${1:?usage: $0 <base-sha> <head-sha>}"
HEAD="${2:?usage: $0 <base-sha> <head-sha>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PACKAGES_JSON="${PACKAGES_JSON:-$REPO_ROOT/.github/actions/get-packages-matrix/package_configuration.json}"

NULL_SHA="0000000000000000000000000000000000000000"

# Paths whose change rebuilds every publishable package. Keep short and
# explicit — anything that can alter the wheel contents or the publish
# machinery itself belongs here.
INVALIDATORS=(
  ".github/workflows/publish-dev.yaml"
  ".github/scripts/rewrite-pyproject-for-dev.py"
  ".github/scripts/detect-changed-packages.sh"
  ".github/scripts/compute-calver.sh"
  ".github/actions/get-packages-matrix/package_configuration.json"
  ".github/actions/publish-to-pypi-with-uv/action.yml"
)

publishable_matrix() {
  jq -c '{include: [.[] | select((.publish_skip != true) and (.pypi_name != null))]}' \
    "$PACKAGES_JSON"
}

if [[ -z "$BASE" || "$BASE" == "$NULL_SHA" ]]; then
  echo "detect-changed-packages: base is null SHA; selecting all publishable packages" >&2
  publishable_matrix
  exit 0
fi

if ! git rev-parse --verify --quiet "${BASE}^{commit}" >/dev/null \
   || ! git rev-parse --verify --quiet "${HEAD}^{commit}" >/dev/null; then
  echo "detect-changed-packages: one of ${BASE}/${HEAD} is not fetched; selecting all publishable packages" >&2
  publishable_matrix
  exit 0
fi

CHANGED="$(git diff --name-only "$BASE" "$HEAD" -- | sort -u)"

if [[ -z "$CHANGED" ]]; then
  echo '{"include":[]}'
  exit 0
fi

for path in "${INVALIDATORS[@]}"; do
  if grep -qxF "$path" <<<"$CHANGED"; then
    echo "detect-changed-packages: invalidator '${path}' changed; selecting all publishable packages" >&2
    publishable_matrix
    exit 0
  fi
done

# Filter packages whose dir prefixes any changed file. `dir + "/"` guards
# against `unique_toolkit_x` spuriously matching `unique_toolkit/`.
jq -c --arg files "$CHANGED" '
  ($files | split("\n") | map(select(length > 0))) as $fs
  | [
      .[]
      | select((.publish_skip != true) and (.pypi_name != null))
      | . as $pkg
      | select(any($fs[]; startswith($pkg.dir + "/")))
    ]
  | {include: .}
' "$PACKAGES_JSON"
