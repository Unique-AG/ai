#!/bin/bash
set -e

# === CONFIGURATION ===
# Azure targets come from SecretSpec (see secretspec.toml).
PORT="${PORT:-8004}"

REQUIRED_SECRETS=(
  AZURE_SUBSCRIPTION_ID
  AZURE_RESOURCE_GROUP
  AZURE_LOCATION
  AZURE_WEBAPP_NAME
  AZURE_CONTAINER_REGISTRY
)

# === LOAD SECRETS ===
# Preferred: inject via SecretSpec + 1Password:
#   ./deploy-with-secrets.sh
# Fallback: source local env files only when a required secret is still missing
# (never overwrite values already injected by secretspec).
needs_fallback=false
for key in "${REQUIRED_SECRETS[@]}"; do
  if [ -z "${!key:-}" ]; then
    needs_fallback=true
    break
  fi
done

if [ "$needs_fallback" = true ]; then
  for f in zitadel.env unique_mcp.env .env; do
    if [ -f "$f" ]; then
      # shellcheck disable=SC1090
      set -a && source "$f" && set +a
      echo "Loaded $f (fallback; prefer secretspec run)"
    fi
  done
fi

missing=()
for key in "${REQUIRED_SECRETS[@]}"; do
  if [ -z "${!key:-}" ]; then
    missing+=("$key")
  fi
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "ERROR: required secret(s) not set: ${missing[*]}"
  echo "Inject with SecretSpec (1Password via nix), then re-run:"
  echo "  secretspec check --profile deploy"
  echo "  secretspec set AZURE_SUBSCRIPTION_ID --profile deploy"
  echo "  secretspec set AZURE_RESOURCE_GROUP --profile deploy"
  echo "  secretspec set AZURE_LOCATION --profile deploy"
  echo "  secretspec set AZURE_WEBAPP_NAME --profile deploy"
  echo "  secretspec set AZURE_CONTAINER_REGISTRY --profile deploy"
  echo "  ./deploy-with-secrets.sh"
  exit 1
fi

# Public URL for OAuth metadata / callbacks. Always use the Azure hostname unless
# PUBLIC_BASE_URL is explicitly overridden.
AZURE_PUBLIC_URL="https://${AZURE_WEBAPP_NAME}.azurewebsites.net"
UNIQUE_MCP_PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$AZURE_PUBLIC_URL}"
UNIQUE_MCP_LOCAL_BASE_URL="http://0.0.0.0:${PORT}"

# === SET SUBSCRIPTION ===
az account set --subscription "$AZURE_SUBSCRIPTION_ID"

# === USE EXISTING RESOURCE GROUP ===
if ! az group show -n "$AZURE_RESOURCE_GROUP" &>/dev/null; then
  echo "ERROR: Resource group '$AZURE_RESOURCE_GROUP' not found."
  echo "Create it first, e.g.:"
  echo "  az group create --name \"$AZURE_RESOURCE_GROUP\" --location \"$AZURE_LOCATION\""
  exit 1
fi
echo "Using resource group '$AZURE_RESOURCE_GROUP' in '$AZURE_LOCATION'"
echo "  webapp=$AZURE_WEBAPP_NAME acr=$AZURE_CONTAINER_REGISTRY"

# === CREATE ACR ===
az acr create -n "$AZURE_CONTAINER_REGISTRY" -g "$AZURE_RESOURCE_GROUP" --sku Basic --admin-enabled true \
  --location "$AZURE_LOCATION" 2>/dev/null || echo "ACR exists"

# === BUILD IMAGE IN AZURE ===
# Stage a small build context with only the packages the Dockerfile needs.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# fastmcp -> account_review -> datasets -> mcp_dashboards -> mcp -> tutorials -> ai
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../../.." && pwd)"
MCP_DASHBOARDS="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BUILD_DIR="$(mktemp -d)"
cleanup_build_dir() { rm -rf "$BUILD_DIR"; }
trap cleanup_build_dir EXIT

echo "Staging build context in ${BUILD_DIR}"
echo "  REPO_ROOT=${REPO_ROOT}"
echo "  MCP_DASHBOARDS=${MCP_DASHBOARDS}"

rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' --exclude '*.db' \
  "${REPO_ROOT}/unique_mcp/" "${BUILD_DIR}/unique_mcp/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' --exclude 'htmlcov' --exclude '.mypy_cache' \
  "${REPO_ROOT}/unique_toolkit/" "${BUILD_DIR}/unique_toolkit/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' \
  "${REPO_ROOT}/unique_sdk/" "${BUILD_DIR}/unique_sdk/"

mkdir -p "${BUILD_DIR}/mcp_dashboards/helpers/python" \
  "${BUILD_DIR}/mcp_dashboards/datasets/account_review/fastmcp"

rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude 'tests' \
  "${MCP_DASHBOARDS}/helpers/python/" "${BUILD_DIR}/mcp_dashboards/helpers/python/"
rsync -a --exclude '.venv' --exclude '__pycache__' --exclude '.pytest_cache' --exclude '.ruff_cache' \
  --exclude 'tests' --exclude '*.sqlite' --exclude '__pycache__' \
  "${SCRIPT_DIR}/" "${BUILD_DIR}/mcp_dashboards/datasets/account_review/fastmcp/"

cp "${SCRIPT_DIR}/Dockerfile" "${BUILD_DIR}/Dockerfile"

az acr build \
  -t "${AZURE_WEBAPP_NAME}:latest" \
  -r "$AZURE_CONTAINER_REGISTRY" \
  -f "${BUILD_DIR}/Dockerfile" \
  "$BUILD_DIR"

cleanup_build_dir
trap - EXIT

# === CREATE APP SERVICE PLAN (B1 ~$13/month) ===
az appservice plan create -n "${AZURE_WEBAPP_NAME}-plan" -g "$AZURE_RESOURCE_GROUP" \
  -l "$AZURE_LOCATION" --is-linux --sku B1 \
  2>/dev/null || echo "App Service plan exists"

# === CREATE WEB APP (or update container if it already exists) ===
az webapp create -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP" -p "${AZURE_WEBAPP_NAME}-plan" \
  --deployment-container-image-name "${AZURE_CONTAINER_REGISTRY}.azurecr.io/${AZURE_WEBAPP_NAME}:latest" \
  2>/dev/null || \
az webapp config container set -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP" \
  --container-image-name "${AZURE_CONTAINER_REGISTRY}.azurecr.io/${AZURE_WEBAPP_NAME}:latest"

# === CONFIGURE ACR ACCESS (admin credentials so App Service can pull) ===
ACR_USER=$(az acr credential show -n "$AZURE_CONTAINER_REGISTRY" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$AZURE_CONTAINER_REGISTRY" --query passwords[0].value -o tsv)
az webapp config container set -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP" \
  --container-image-name "${AZURE_CONTAINER_REGISTRY}.azurecr.io/${AZURE_WEBAPP_NAME}:latest" \
  --container-registry-url "https://${AZURE_CONTAINER_REGISTRY}.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

# === SET PORT AND APP SETTINGS ===
SETTINGS="WEBSITES_PORT=${PORT}"
SETTINGS="$SETTINGS UNIQUE_MCP_PUBLIC_BASE_URL=${UNIQUE_MCP_PUBLIC_BASE_URL}"
SETTINGS="$SETTINGS UNIQUE_MCP_LOCAL_BASE_URL=${UNIQUE_MCP_LOCAL_BASE_URL}"
SETTINGS="$SETTINGS EXCEL_PATH=/app/dataset/data/account_review_dataset.xlsx"
# /home is persisted on Azure App Service Linux
SETTINGS="$SETTINGS SQLITE_PATH=/home/data/account_review.sqlite"
# FastMCP HostOriginGuard: allow Azure hostname (JSON list for pydantic-settings)
PUBLIC_HOST="${UNIQUE_MCP_PUBLIC_BASE_URL#https://}"
PUBLIC_HOST="${PUBLIC_HOST#http://}"
PUBLIC_HOST="${PUBLIC_HOST%%/*}"
SETTINGS="$SETTINGS FASTMCP_HTTP_ALLOWED_HOSTS=[\"${PUBLIC_HOST}\"]"

# Auth: enable Zitadel when credentials are present; otherwise demo mode.
# Override explicitly with AUTH_DISABLED=true|false.
if [ -z "${AUTH_DISABLED:-}" ]; then
  if [ -n "${ZITADEL_CLIENT_ID:-}" ] && [ -n "${ZITADEL_CLIENT_SECRET:-}" ]; then
    AUTH_DISABLED=false
  else
    AUTH_DISABLED=true
  fi
fi
SETTINGS="$SETTINGS AUTH_DISABLED=$AUTH_DISABLED"
[ -n "${ZITADEL_BASE_URL:-}" ] && SETTINGS="$SETTINGS ZITADEL_BASE_URL=$ZITADEL_BASE_URL"
[ -n "${ZITADEL_CLIENT_ID:-}" ] && SETTINGS="$SETTINGS ZITADEL_CLIENT_ID=$ZITADEL_CLIENT_ID"
[ -n "${ZITADEL_CLIENT_SECRET:-}" ] && SETTINGS="$SETTINGS ZITADEL_CLIENT_SECRET=$ZITADEL_CLIENT_SECRET"

az webapp config appsettings set -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP" --settings $SETTINGS

# === ENABLE ALWAYS ON ===
az webapp config set -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP" --always-on true

# === RESTART TO PULL LATEST IMAGE ===
az webapp restart -n "$AZURE_WEBAPP_NAME" -g "$AZURE_RESOURCE_GROUP"

echo ""
echo "Done! Admin UI: https://${AZURE_WEBAPP_NAME}.azurewebsites.net/"
echo "Status JSON:  https://${AZURE_WEBAPP_NAME}.azurewebsites.net/api/status"
echo "MCP endpoint: https://${AZURE_WEBAPP_NAME}.azurewebsites.net/mcp"
echo ""
echo "Zitadel redirect URI (register in your OAuth app):"
echo "  https://${AZURE_WEBAPP_NAME}.azurewebsites.net/auth/callback"
echo ""
echo "Required app settings for production auth:"
echo "  ZITADEL_BASE_URL, ZITADEL_CLIENT_ID, ZITADEL_CLIENT_SECRET"
echo "  UNIQUE_MCP_PUBLIC_BASE_URL=${UNIQUE_MCP_PUBLIC_BASE_URL}"
