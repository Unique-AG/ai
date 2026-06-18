#!/usr/bin/env bash
# render-values-schema.sh — render values.schema.json for every dedicated helm
# chart by pulling the base schema from the OCI artifact pinned in each chart's
# Chart.yaml and deep-merging with a sibling values.additional.schema.json when
# present.
#
# Usage:
#   scripts/render-values-schema.sh          # apply
#   scripts/render-values-schema.sh --check  # exit 1 if any copy is out of sync
#
# Prerequisites: git; helm (logged in to ghcr.io); jq (only when
#   values.additional.schema.json is present)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"
OCI_REGISTRY="oci://ghcr.io/unique-ag/helm"

# jq program for deep-merging two JSON Schema objects.
# Merge semantics match the monorepo's render-values-schema.sh:
#   "required" arrays  — union (base order first, no duplicates)
#   "allOf"/"anyOf"/"oneOf" arrays — concatenate (base first) when key exists in both
#   Both-object values — recurse
#   All other cases    — additional wins
DEEP_MERGE_JQ=$(cat << 'JQEOF'
def array_union(a; b):
  a + [b[] | . as $item | select((a | map(. == $item) | any) | not)];

def deep_merge(add):
  . as $src |
  reduce (add | keys_unsorted[]) as $k (
    $src;
    if $k == "required" then
      .[$k] = array_union(($src[$k] // []); (add[$k] // []))
    elif ($k == "allOf" or $k == "anyOf" or $k == "oneOf") and ($src | has($k)) then
      .[$k] = $src[$k] + add[$k]
    elif ($src | has($k)) and ($src[$k] | type) == "object" and (add[$k] | type) == "object" then
      .[$k] = ($src[$k] | deep_merge(add[$k]))
    else
      .[$k] = add[$k]
    end
  );

$base[0] | deep_merge($additional[0])
JQEOF
)

run_merge() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq is required for deep-merge but was not found on PATH." >&2
    exit 1
  fi
  jq -n \
    --slurpfile base "$1" \
    --slurpfile additional "$2" \
    "${DEEP_MERGE_JQ}"
}

# Extract the version of the 'base' dependency from a Chart.yaml.
# Finds the line after 'name: base' that contains 'version:'.
get_base_version() {
  local chart_yaml="$1"
  awk '/name: base/{found=1} found && /version:/{gsub(/[" \t]/, "", $2); print $2; exit}' "${chart_yaml}"
}

# Pull the base chart .tgz from OCI and extract values.schema.json.
# Caches by version: skips pull when the schema has already been extracted
# into the version-keyed subdirectory under PULL_TMPDIR.
PULL_TMPDIR=""

get_base_schema() {
  local version="$1"

  if [[ -z "${PULL_TMPDIR}" ]]; then
    PULL_TMPDIR=$(mktemp -d)
  fi

  local schema_path="${PULL_TMPDIR}/${version}/base/values.schema.json"
  if [[ -f "${schema_path}" ]]; then
    echo "${schema_path}"
    return
  fi

  if ! command -v helm >/dev/null 2>&1; then
    echo "Error: helm is required to pull the base chart from the OCI registry." >&2
    exit 1
  fi

  local version_dir="${PULL_TMPDIR}/${version}"
  mkdir -p "${version_dir}"

  helm pull "${OCI_REGISTRY}/base" --version "${version}" --destination "${version_dir}" >/dev/null 2>&1
  local tgz
  tgz=$(ls "${version_dir}"/*.tgz)
  tar -xzf "${tgz}" -C "${version_dir}" base/values.schema.json

  echo "${schema_path}"
}

cleanup() {
  [[ -n "${tmpfile:-}" ]] && rm -f "${tmpfile}" || true
  [[ -n "${PULL_TMPDIR:-}" ]] && rm -rf "${PULL_TMPDIR}" || true
}
trap cleanup EXIT

CHECK=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK=true
fi

cd "${REPO_ROOT}"

tmpfile=$(mktemp)

drift=0
synced=0

while IFS= read -r dst; do
  [[ -z "${dst}" ]] && continue
  [[ ! -f "${dst}" ]] && continue

  chart_yaml="${dst%values.schema.json}Chart.yaml"
  if [[ ! -f "${chart_yaml}" ]]; then
    echo "  warning: no Chart.yaml found alongside ${dst}, skipping" >&2
    continue
  fi

  version=$(get_base_version "${chart_yaml}")
  if [[ -z "${version}" ]]; then
    echo "  warning: could not determine base dependency version from ${chart_yaml}, skipping" >&2
    continue
  fi

  base_schema=$(get_base_schema "${version}")

  add="${dst%values.schema.json}values.additional.schema.json"

  if [[ ! -f "${add}" ]]; then
    cp "${base_schema}" "${tmpfile}"
  else
    run_merge "${base_schema}" "${add}" > "${tmpfile}"
  fi

  if cmp -s "${dst}" "${tmpfile}"; then
    continue
  fi

  if [[ "${CHECK}" == "true" ]]; then
    echo "  drift -> ${dst}"
    drift=$((drift + 1))
  else
    cp "${tmpfile}" "${dst}"
    echo "  synced -> ${dst}"
    synced=$((synced + 1))
  fi
done < <(git ls-files ':(glob)**/deploy/helm-chart/values.schema.json' ':(glob)**/deploy/*/helm-chart/values.schema.json')

if [[ "${CHECK}" == "true" ]]; then
  if [[ ${drift} -gt 0 ]]; then
    echo ""
    echo "Error: ${drift} dedicated chart(s) have a values.schema.json that is out of sync." >&2
    echo "Run scripts/render-values-schema.sh to fix." >&2
    exit 1
  fi
  echo "All dedicated chart values.schema.json files are in sync."
else
  echo ""
  echo "Synced ${synced} chart(s)."
fi
