#!/bin/bash
set -e

# === CONFIGURATION ===
# Reuse the same resource group as tutorials/mcp/mcp_search (override with RG=...).
RG="${RG:-rg-lab-demo-001-unique-search-mcp}"
APP="${APP:-sqlite-excel-mcp}"
ACR="${ACR:-sqliteexcelmcpacr}"
PORT="${PORT:-8004}"

# === LOAD ENV VARS ===
# Prefer the same split env files as mcp_search; fall back to .env
for f in zitadel.env unique_mcp.env .env; do
  if [ -f "$f" ]; then
    # shellcheck disable=SC1090
    set -a && source "$f" && set +a
    echo "Loaded $f"
  fi
done

SUBSCRIPTION="${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID in .env}"

# Public URL for OAuth metadata / callbacks. Always use the Azure hostname unless
# PUBLIC_BASE_URL is explicitly overridden (local unique_mcp.env often points at localhost).
AZURE_PUBLIC_URL="https://${APP}.azurewebsites.net"
UNIQUE_MCP_PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$AZURE_PUBLIC_URL}"
UNIQUE_MCP_LOCAL_BASE_URL="http://0.0.0.0:${PORT}"

# === SET SUBSCRIPTION ===
az account set --subscription "$SUBSCRIPTION"

# === USE EXISTING RESOURCE GROUP (from mcp_search) ===
if ! az group show -n "$RG" &>/dev/null; then
  echo "ERROR: Resource group '$RG' not found."
  echo "Create it first (same as mcp_search), e.g.:"
  echo "  az group create --name rg-lab-demo-001-unique-search-mcp --location swedencentral"
  exit 1
fi
LOCATION="${LOCATION:-$(az group show -n "$RG" --query location -o tsv)}"
echo "Using resource group '$RG' in '$LOCATION'"

# === CREATE ACR ===
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || echo "ACR exists"

# === BUILD IMAGE IN AZURE ===
# Stage a small build context with only the packages the Dockerfile needs.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BUILD_DIR="$(mktemp -d)"
cleanup_build_dir() { rm -rf "$BUILD_DIR"; }
trap cleanup_build_dir EXIT

echo "Staging build context in ${BUILD_DIR}"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' --exclude '*.db' \
  "${REPO_ROOT}/unique_mcp/" "${BUILD_DIR}/unique_mcp/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' --exclude 'htmlcov' --exclude '.mypy_cache' \
  "${REPO_ROOT}/unique_toolkit/" "${BUILD_DIR}/unique_toolkit/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' \
  "${REPO_ROOT}/unique_sdk/" "${BUILD_DIR}/unique_sdk/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' --exclude '*.db' \
  "${SCRIPT_DIR}/" "${BUILD_DIR}/mcp_sqlite_excel/"
cp "${SCRIPT_DIR}/Dockerfile" "${BUILD_DIR}/Dockerfile"

az acr build \
  -t "$APP:latest" \
  -r "$ACR" \
  -f "${BUILD_DIR}/Dockerfile" \
  "$BUILD_DIR"

cleanup_build_dir
trap - EXIT

# === CREATE APP SERVICE PLAN (B1 ~$13/month) ===
az appservice plan create -n "${APP}-plan" -g "$RG" -l "$LOCATION" --is-linux --sku B1 \
  2>/dev/null || echo "App Service plan exists"

# === CREATE WEB APP (or update container if it already exists) ===
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" \
  2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS (admin credentials so App Service can pull) ===
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest" \
  --container-registry-url "https://${ACR}.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

# === SET PORT AND APP SETTINGS ===
SETTINGS="WEBSITES_PORT=${PORT}"
SETTINGS="$SETTINGS UNIQUE_MCP_PUBLIC_BASE_URL=${UNIQUE_MCP_PUBLIC_BASE_URL}"
SETTINGS="$SETTINGS UNIQUE_MCP_LOCAL_BASE_URL=${UNIQUE_MCP_LOCAL_BASE_URL}"
SETTINGS="$SETTINGS EXCEL_PATH=/app/data/account_review_dataset.xlsx"
# /home is persisted on Azure App Service Linux
SETTINGS="$SETTINGS SQLITE_PATH=/home/data/portfolio.db"
# FastMCP HostOriginGuard: allow Azure hostname (JSON list for pydantic-settings)
PUBLIC_HOST="${UNIQUE_MCP_PUBLIC_BASE_URL#https://}"
PUBLIC_HOST="${PUBLIC_HOST#http://}"
PUBLIC_HOST="${PUBLIC_HOST%%/*}"
SETTINGS="$SETTINGS FASTMCP_HTTP_ALLOWED_HOSTS=[\"${PUBLIC_HOST}\"]"

# Demo escape hatch: AUTH_DISABLED=true skips Zitadel (do not use in real prod).
[ -n "$AUTH_DISABLED" ] && SETTINGS="$SETTINGS AUTH_DISABLED=$AUTH_DISABLED"
[ -n "$ZITADEL_BASE_URL" ] && SETTINGS="$SETTINGS ZITADEL_BASE_URL=$ZITADEL_BASE_URL"
[ -n "$ZITADEL_CLIENT_ID" ] && SETTINGS="$SETTINGS ZITADEL_CLIENT_ID=$ZITADEL_CLIENT_ID"
[ -n "$ZITADEL_CLIENT_SECRET" ] && SETTINGS="$SETTINGS ZITADEL_CLIENT_SECRET=$ZITADEL_CLIENT_SECRET"

az webapp config appsettings set -n "$APP" -g "$RG" --settings $SETTINGS

# === ENABLE ALWAYS ON ===
az webapp config set -n "$APP" -g "$RG" --always-on true

# === RESTART TO PULL LATEST IMAGE ===
az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo ""
echo "Zitadel redirect URI (register in your OAuth app):"
echo "  https://${APP}.azurewebsites.net/auth/callback"
echo ""
echo "Required app settings for production auth:"
echo "  ZITADEL_BASE_URL, ZITADEL_CLIENT_ID, ZITADEL_CLIENT_SECRET"
echo "  UNIQUE_MCP_PUBLIC_BASE_URL=${UNIQUE_MCP_PUBLIC_BASE_URL}"
