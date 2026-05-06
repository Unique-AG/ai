#!/bin/bash
set -e

# === CONFIGURATION ===
RG="rg-lab-demo-001-unique-companies-house-mcp"
LOCATION="swedencentral"
APP="companies-house-mcp"
ACR="companieshousemcpacr"
# === LOAD ENV VARS ===
if [ -f .env ]; then
  source .env
  echo "Loaded .env"
else
  echo "Warning: .env file not found — app settings will not be configured"
fi

SUBSCRIPTION="${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID in .env}"

# === SET SUBSCRIPTION ===
az account set --subscription "$SUBSCRIPTION"

# === CREATE ACR ===
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || echo "ACR exists"

# === BUILD IMAGE IN AZURE ===
az acr build -t "$APP:latest" -r "$ACR" .

# === CREATE APP SERVICE PLAN (B1 ~$13/month) ===
az appservice plan create -n "${APP}-plan" -g "$RG" -l "$LOCATION" --is-linux --sku B1

# === CREATE WEB APP ===
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS ===
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io"

# === SET PORT AND APP SETTINGS ===
SETTINGS="WEBSITES_PORT=3001"
[ -n "$COMPANIES_HOUSE_API_KEY" ] && SETTINGS="$SETTINGS COMPANIES_HOUSE_API_KEY=$COMPANIES_HOUSE_API_KEY"
[ -n "$COMPANIES_HOUSE_SANDBOX" ] && SETTINGS="$SETTINGS COMPANIES_HOUSE_SANDBOX=$COMPANIES_HOUSE_SANDBOX"
[ -n "$MCP_CLIENT_ID" ] && SETTINGS="$SETTINGS MCP_CLIENT_ID=$MCP_CLIENT_ID"
[ -n "$MCP_CLIENT_SECRET" ] && SETTINGS="$SETTINGS MCP_CLIENT_SECRET=$MCP_CLIENT_SECRET"
az webapp config appsettings set -n "$APP" -g "$RG" --settings $SETTINGS

# === ENABLE ALWAYS ON ===
az webapp config set -n "$APP" -g "$RG" --always-on true

# === RESTART TO PULL LATEST IMAGE ===
az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
