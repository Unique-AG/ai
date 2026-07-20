#!/bin/bash
set -e

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-unique-space-chat-mcp}"
LOCATION="${LOCATION:-swedencentral}"
APP="${APP:-unique-space-chat-mcp}"
ACR="${ACR:-uniquespacechatmcpacr}"
PLAN="${PLAN:-${APP}-plan}"

# === SET SUBSCRIPTION ===
echo "[1/6] Setting subscription..."
az account set --subscription "$SUBSCRIPTION"

# === CREATE ACR (idempotent) ===
echo "[2/6] ACR and build..."
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || true
az acr build -t "${APP}:latest" -r "$ACR" .

# Pin the Web App to the immutable digest of the image we just built
# (not the mutable :latest tag).
IMAGE_DIGEST="$(
  az acr repository show \
    -n "$ACR" \
    --image "${APP}:latest" \
    --query digest \
    -o tsv
)"
if [[ -z "${IMAGE_DIGEST}" || "${IMAGE_DIGEST}" == "null" ]]; then
  echo "ERROR: could not resolve image digest for ${ACR}.azurecr.io/${APP}:latest" >&2
  exit 1
fi
IMAGE_REF="${ACR}.azurecr.io/${APP}@${IMAGE_DIGEST}"
echo "Deploying image: ${IMAGE_REF}"

# === CREATE APP SERVICE PLAN + WEB APP ===
echo "[3/6] App Service plan..."
az appservice plan create -n "$PLAN" -g "$RG" --is-linux --sku B1 2>/dev/null || true

# === CREATE WEB APP (or update if exists) ===
echo "[4/6] Web App..."
az webapp create -n "$APP" -g "$RG" -p "$PLAN" \
  --deployment-container-image-name "${IMAGE_REF}" 2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${IMAGE_REF}"

# === CONFIGURE ACR ACCESS ===
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io" \
  --container-image-name "${IMAGE_REF}"

# === SET PORT AND ALWAYS ON ===
echo "[5/6] Port and Always On..."
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8004 -o none
az webapp config set -n "$APP" -g "$RG" --always-on true -o none

# === APP ENVIRONMENT VARIABLES (non-secret) ===
echo "[6/6] App settings..."
az webapp config appsettings set -n "$APP" -g "$RG" -o none --settings \
  UNIQUE_MCP_LOCAL_BASE_URL="http://0.0.0.0:8004" \
  UNIQUE_MCP_PUBLIC_BASE_URL="https://${APP}.azurewebsites.net" \
  UNIQUE_FRONTEND_BASE_URL="${UNIQUE_FRONTEND_BASE_URL:-https://next.qa.unique.app}" \
  FASTMCP_HTTP_ALLOWED_HOSTS="[\"${APP}.azurewebsites.net\"]" \
  FASTMCP_HTTP_ALLOWED_ORIGINS="[\"https://${APP}.azurewebsites.net\",\"https://id.qa.unique.app\",\"http://localhost:8765\",\"http://127.0.0.1:8765\"]"

az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo "Image: ${IMAGE_REF}"
echo ""
echo "IMPORTANT: Set app + Zitadel secrets via Azure Portal or CLI:"
echo "  az webapp config appsettings set -n $APP -g $RG --settings \\"
echo "    UNIQUE_APP_KEY=... UNIQUE_APP_ID=... UNIQUE_API_BASE_URL=... \\"
echo "    UNIQUE_APP_ENDPOINT=... UNIQUE_APP_ENDPOINT_SECRET=... \\"
echo "    ZITADEL_BASE_URL=... ZITADEL_CLIENT_ID=... ZITADEL_CLIENT_SECRET=..."
echo ""
echo "Do NOT set UNIQUE_AUTH_USER_ID / UNIQUE_AUTH_COMPANY_ID on the Web App."
echo "Chat identity comes from the logged-in OAuth user (JWT / userinfo)."
echo ""
echo "Chat embed uses UNIQUE_FRONTEND_BASE_URL (default https://next.qa.unique.app):"
echo "  {UNIQUE_FRONTEND_BASE_URL}/chat/embed/{chatId}?spaceId={spaceId}"
echo ""
echo "Also register the OAuth redirect URI in Zitadel:"
echo "  https://${APP}.azurewebsites.net/auth/callback"
echo ""
echo "Platform prerequisites for the embedded chat window:"
echo "  - Chat app CSP frame-ancestors must allowlist the MCP host sandbox origin"
echo "  - See README.md / docs for Claude (*.claudemcpcontent.com) and MCP-UI hosts"
