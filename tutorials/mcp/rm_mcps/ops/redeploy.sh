#!/usr/bin/env bash
# Rebuild + repoint + restart the deployed RM MCP servers on Azure.
#
# Usage: ./redeploy.sh [advisory|crm|both]   (default: both)
#
# IMPORTANT: the web apps are PINNED to timestamp tags (e.g. rm-crm-mcp:20260629111633),
# NOT :latest. Building :latest and restarting does NOTHING. This script builds a fresh
# timestamp tag, points the web app at it (config container set), and restarts.
#
# NOTE: SQL seed files are baked into the image. After redeploying, new/changed seed
# data only takes effect after running the Reset_Demo_Data tool (chat UI: "reset the
# demo data"). Resetting BEFORE redeploy restores OLD data.
set -euo pipefail

SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-rm-agent-mcp}"
ACR="${ACR:-rmmcpsacr}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # tutorials/mcp/rm_mcps
TAG="$(date -u +%Y%m%d%H%M%S)"

TARGET="${1:-both}"

deploy() {
  local name="$1" dir="$2"
  echo "==> Building $name:$TAG from $dir ..."
  az acr build --subscription "$SUBSCRIPTION" --registry "$ACR" \
    --image "$name:$TAG" --image "$name:latest" "$dir"
  echo "==> Pointing $name at $ACR.azurecr.io/$name:$TAG ..."
  az webapp config container set --subscription "$SUBSCRIPTION" -g "$RG" -n "$name" \
    --container-image-name "$ACR.azurecr.io/$name:$TAG" --output none
  echo "==> Restarting $name ..."
  az webapp restart --subscription "$SUBSCRIPTION" -g "$RG" -n "$name"
  echo "==> $name redeployed at tag $TAG."
}

case "$TARGET" in
  advisory) deploy rm-advisory-mcp "$HERE/mcp_advisory" ;;
  crm)      deploy rm-crm-mcp      "$HERE/mcp_crm" ;;
  both)     deploy rm-advisory-mcp "$HERE/mcp_advisory"
            deploy rm-crm-mcp      "$HERE/mcp_crm" ;;
  *) echo "usage: $0 [advisory|crm|both]" >&2; exit 1 ;;
esac

echo "Done. Verify with: python3 $HERE/ops/mcp_call.py https://rm-crm-mcp.azurewebsites.net/mcp list"
