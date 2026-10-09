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

# Safe defaults: the policy renders from values.yaml alone, and the guard blocks disabling it.
render_defaults() {
  helm template search-proxy "${CHART_DIR}" \
    -f "${CHART_DIR}/values.yaml" \
    --namespace search-proxy \
    --api-versions cilium.io/v2 \
    "$@"
}
policy="$(render_defaults)"
for expected in "k8s:app.kubernetes.io/name: assistants-core" "k8s:io.kubernetes.pod.namespace: chat" "k8s:io.kubernetes.pod.namespace: system"; do
  if ! grep -qF "${expected}" <<<"${policy}"; then
    echo "Error: default policy is missing '${expected}'." >&2
    exit 1
  fi
done
err="$(render_defaults --set networkPolicy.enabled=false 2>&1 >/dev/null || true)"
if ! grep -qF "networkPolicy is off" <<<"${err}"; then
  echo "Error: networkPolicy.enabled=false did not trip the guard." >&2
  exit 1
fi
if render_defaults --set networkPolicy.enabled=false --set-string networkPolicy.allowDisabled=true >/dev/null 2>&1; then
  echo "Error: a string allowDisabled passed the schema." >&2
  exit 1
fi
render_defaults --set networkPolicy.enabled=false --set networkPolicy.allowDisabled=true >/dev/null

# Strict mode drops the world egress rule but keeps the proxy rule; it needs a proxy.
if grep -qF "toEntities" "${OUT_DIR}/values-proxy-strict.yaml" || ! grep -qF 'matchName: "proxy.corp.example"' "${OUT_DIR}/values-proxy-strict.yaml"; then
  echo "Error: strict fixture must drop world egress and keep the proxy rule." >&2
  exit 1
fi
if ! grep -qF "toEntities" <<<"${policy}"; then
  echo "Error: default policy is missing the world egress rule." >&2
  exit 1
fi
err="$(render_defaults --set networkPolicy.allowWorldEgress=false 2>&1 >/dev/null || true)"
if ! grep -qF "allowWorldEgress=false needs" <<<"${err}"; then
  echo "Error: allowWorldEgress=false without a proxy did not trip the guard." >&2
  exit 1
fi

# A configured proxy gets its own egress rule: FQDN from the fixture, /32 CIDR for an IPv4 host.
if ! grep -qF 'matchName: "proxy.corp.example"' "${OUT_DIR}/values-proxy-enabled.yaml" \
  || ! grep -qF 'port: "3128"' "${OUT_DIR}/values-proxy-enabled.yaml"; then
  echo "Error: proxy fixture is missing its egress rule." >&2
  exit 1
fi
for bad in "999.1.1.1" "fd00::1" "http://proxy.corp:3128" "10.0.0.0/8"; do
  if render_defaults --set-string "httpClient.connection.proxyHost=${bad}" --set httpClient.connection.proxyPort=3128 >/dev/null 2>&1; then
    echo "Error: proxyHost '${bad}' rendered instead of failing." >&2
    exit 1
  fi
done
if render_defaults --set httpClient.connection.proxyHost=proxy.corp --set httpClient.connection.proxyPort=70000 >/dev/null 2>&1; then
  echo "Error: proxyPort 70000 rendered instead of failing." >&2
  exit 1
fi
if ! render_defaults --set httpClient.connection.proxyHost=10.1.2.3 --set httpClient.connection.proxyPort=3128 | grep -qF '"10.1.2.3/32"'; then
  echo "Error: an IPv4 proxy host did not render a /32 toCIDR rule." >&2
  exit 1
fi

if [[ "${CHECK}" == "true" ]]; then
  echo "All fixtures rendered successfully."
fi
