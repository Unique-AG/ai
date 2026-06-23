#!/usr/bin/env bash
# render-helm-docs.sh — generate README.md for every dedicated helm chart using
# helm-docs (https://github.com/norwoodj/helm-docs). Artifact Hub renders the
# packaged README on the chart page.
#
# Usage:
#   scripts/render-helm-docs.sh                         # all charts
#   scripts/render-helm-docs.sh --check                 # exit 1 on drift
#   scripts/render-helm-docs.sh path/to/helm-chart      # one chart
#   scripts/render-helm-docs.sh --check path/to/chart   # one chart, check only
#
# Prerequisites: git; helm-docs on PATH (brew install norwoodj/tap/helm-docs)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel)"

CHECK=false
CHART_DIRS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      CHECK=true
      shift
      ;;
    -*)
      echo "Error: unknown option: $1" >&2
      exit 1
      ;;
    *)
      CHART_DIRS+=("$1")
      shift
      ;;
  esac
done

if ! command -v helm-docs >/dev/null 2>&1; then
  echo "Error: helm-docs is required but was not found on PATH." >&2
  echo "Install: brew install norwoodj/tap/helm-docs" >&2
  exit 1
fi

if [[ ${#CHART_DIRS[@]} -eq 0 ]]; then
  while IFS= read -r chart_yaml; do
    [[ -z "${chart_yaml}" ]] && continue
    CHART_DIRS+=("$(dirname "${chart_yaml}")")
  done < <(git -C "${REPO_ROOT}" ls-files ':(glob)**/deploy/helm-chart/Chart.yaml' ':(glob)**/deploy/*/helm-chart/Chart.yaml')
fi

if [[ ${#CHART_DIRS[@]} -eq 0 ]]; then
  echo "No dedicated helm charts found."
  exit 0
fi

cd "${REPO_ROOT}"

drift=0
synced=0

for chart_dir in "${CHART_DIRS[@]}"; do
  if [[ ! -f "${chart_dir}/Chart.yaml" ]]; then
    echo "  warning: no Chart.yaml in ${chart_dir}, skipping" >&2
    continue
  fi

  readme="${chart_dir}/README.md"
  before=$(mktemp)
  if [[ -f "${readme}" ]]; then
    cp "${readme}" "${before}"
  else
    : > "${before}"
  fi

  helm-docs --chart-search-root "${chart_dir}" >/dev/null

  if [[ "${CHECK}" == "true" ]]; then
    after=$(mktemp)
    cp "${readme}" "${after}"

    if [[ -s "${before}" ]]; then
      cp "${before}" "${readme}"
    else
      rm -f "${readme}"
    fi

    if ! cmp -s "${before}" "${after}"; then
      echo "  drift -> ${readme}"
      drift=$((drift + 1))
    fi
    rm -f "${after}"
  elif ! cmp -s "${readme}" "${before}" 2>/dev/null; then
    echo "  synced -> ${readme}"
    synced=$((synced + 1))
  fi

  rm -f "${before}"
done

if [[ "${CHECK}" == "true" ]]; then
  if [[ ${drift} -gt 0 ]]; then
    echo ""
    echo "Error: ${drift} chart README.md file(s) are out of sync with helm-docs." >&2
    echo "Run scripts/render-helm-docs.sh to fix." >&2
    exit 1
  fi
  echo "All dedicated chart README.md files are in sync."
else
  echo ""
  echo "Synced ${synced} chart README(s)."
fi
