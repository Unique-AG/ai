#!/bin/bash
set -e

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-unique-search-mcp}"
LOCATION="${LOCATION:-swedencentral}"
APP="${APP:-unique-search-mcp}"
ACR="${ACR:-uniquesearchmcpacr}"
PLAN="${PLAN:-${APP}-plan}"

# === SET SUBSCRIPTION ===
echo "[1/6] Setting subscription..."
az account set --subscription "$SUBSCRIPTION"

# === CREATE ACR (idempotent) ===
echo "[2/6] ACR and build..."
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || true
az acr build -t "${APP}:latest" -r "$ACR" .

# === CREATE APP SERVICE PLAN + WEB APP ===
echo "[3/6] App Service plan..."
az appservice plan create -n "$PLAN" -g "$RG" --is-linux --sku B1 2>/dev/null || true

# === CREATE WEB APP (or update if exists) ===
echo "[4/6] Web App..."
az webapp create -n "$APP" -g "$RG" -p "$PLAN" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" 2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS ===
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io"

# === SET PORT AND ALWAYS ON ===
echo "[5/6] Port and Always On..."
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8003 -o none
az webapp config set -n "$APP" -g "$RG" --always-on true -o none

# === APP ENVIRONMENT VARIABLES (non-secret) ===
echo "[6/6] App settings..."
az webapp config appsettings set -n "$APP" -g "$RG" -o none --settings \
  UNIQUE_MCP_LOCAL_BASE_URL="http://0.0.0.0:8003" \
  UNIQUE_MCP_PUBLIC_BASE_URL="https://${APP}.azurewebsites.net"

az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo ""
echo "IMPORTANT: Set the required secrets via Azure Portal or CLI:"
echo "  az webapp config appsettings set -n $APP -g $RG --settings \\"
echo "    UNIQUE_APP_KEY=... UNIQUE_APP_ID=... UNIQUE_API_BASE_URL=... \\"
echo "    UNIQUE_AUTH_COMPANY_ID=... UNIQUE_AUTH_USER_ID=... \\"
echo "    UNIQUE_APP_ENDPOINT=... UNIQUE_APP_ENDPOINT_SECRET=... \\"
echo "    ZITADEL_BASE_URL=... ZITADEL_CLIENT_ID=... ZITADEL_CLIENT_SECRET=..."
echo ""
echo "Also register the OAuth redirect URI in Zitadel:"
echo "  https://${APP}.azurewebsites.net/auth/callback"
