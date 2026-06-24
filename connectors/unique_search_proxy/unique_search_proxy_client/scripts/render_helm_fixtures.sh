#!/usr/bin/env bash
# render_helm_fixtures.sh — render helm-chart fixtures with helm template.
#
# Usage (from unique_search_proxy_client/):
#   scripts/render_helm_fixtures.sh
#   scripts/render_helm_fixtures.sh --check   # fail if render errors
#
# Prerequisites: helm (logged in to ghcr.io for base chart dependency)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHART_DIR="${CLIENT_ROOT}/deploy/helm-chart"
FIXTURES_DIR="${CHART_DIR}/fixtures"
OUT_DIR="${CLIENT_ROOT}/.helm-render"

CHECK=false
if [[ "${1:-}" == "--check" ]]; then
  CHECK=true
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "Error: helm is required (brew install helm)." >&2
  exit 1
fi

helm dependency build "${CHART_DIR}" >/dev/null

mkdir -p "${OUT_DIR}"
failed=0

shopt -s nullglob
for fixture in "${FIXTURES_DIR}"/values-*.yaml; do
  name="$(basename "${fixture}" .yaml)"
  out="${OUT_DIR}/${name}.yaml"
  echo "Rendering ${name}..."
  if helm template search-proxy "${CHART_DIR}" \
    -f "${CHART_DIR}/values.yaml" \
    -f "${fixture}" \
    --namespace search-proxy \
    --api-versions cilium.io/v2 \
    --api-versions cilium.io/v2/CiliumNetworkPolicy \
    --api-versions cilium.io/v2/CiliumClusterwideNetworkPolicy \
    > "${out}"; then
    echo "  -> ${out}"
  else
    echo "  FAILED: ${fixture}" >&2
    failed=$((failed + 1))
  fi
done

if [[ ${failed} -gt 0 ]]; then
  echo "Error: ${failed} fixture(s) failed to render." >&2
  exit 1
fi

if [[ "${CHECK}" == "true" ]]; then
  echo "All fixtures rendered successfully."
fi
