#!/bin/bash
set -e

# === CONFIGURATION ===
RG="rg-lab-demo-001-sqlite-excel-mcp"
LOCATION="swedencentral"
APP="sqlite-excel-mcp"
ACR="sqliteexcelmcpacr"
PORT=8004

# === LOAD ENV VARS ===
if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
  echo "Loaded .env"
else
  echo "Warning: .env file not found — OAuth/app secrets will not be configured from file"
fi

SUBSCRIPTION="${AZURE_SUBSCRIPTION_ID:?Set AZURE_SUBSCRIPTION_ID in .env}"

# Public URL used by the OAuth proxy (override with BASE_URL_ENV in .env if needed)
BASE_URL_ENV="${BASE_URL_ENV:-https://${APP}.azurewebsites.net}"

# === SET SUBSCRIPTION ===
az account set --subscription "$SUBSCRIPTION"

# === CREATE RESOURCE GROUP (idempotent) ===
az group create -n "$RG" -l "$LOCATION" 2>/dev/null || echo "Resource group exists"

# === CREATE ACR ===
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || echo "ACR exists"

# === BUILD IMAGE IN AZURE ===
az acr build -t "$APP:latest" -r "$ACR" .

# === CREATE APP SERVICE PLAN (B1 ~$13/month) ===
az appservice plan create -n "${APP}-plan" -g "$RG" -l "$LOCATION" --is-linux --sku B1 \
  2>/dev/null || echo "App Service plan exists"

# === CREATE WEB APP (or update container if it already exists) ===
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" \
  2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS ===
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === SET PORT AND APP SETTINGS ===
# HOST must be 0.0.0.0 so App Service can reach the container.
SETTINGS="WEBSITES_PORT=${PORT} PORT=${PORT} HOST=0.0.0.0"
SETTINGS="$SETTINGS BASE_URL_ENV=${BASE_URL_ENV}"
SETTINGS="$SETTINGS EXCEL_PATH=/app/data/sample_portfolio.xlsx"
# /home is persisted on Azure App Service Linux
SETTINGS="$SETTINGS SQLITE_PATH=/home/data/portfolio.db"

[ -n "$AUTH_DISABLED" ] && SETTINGS="$SETTINGS AUTH_DISABLED=$AUTH_DISABLED"
[ -n "$ZITADEL_URL" ] && SETTINGS="$SETTINGS ZITADEL_URL=$ZITADEL_URL"
[ -n "$UPSTREAM_CLIENT_ID" ] && SETTINGS="$SETTINGS UPSTREAM_CLIENT_ID=$UPSTREAM_CLIENT_ID"
[ -n "$UPSTREAM_CLIENT_SECRET" ] && SETTINGS="$SETTINGS UPSTREAM_CLIENT_SECRET=$UPSTREAM_CLIENT_SECRET"

az webapp config appsettings set -n "$APP" -g "$RG" --settings $SETTINGS

# === ENABLE ALWAYS ON ===
az webapp config set -n "$APP" -g "$RG" --always-on true

# === RESTART TO PULL LATEST IMAGE ===
az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo ""
echo "If using Zitadel OAuth, set the redirect URI to:"
echo "  https://${APP}.azurewebsites.net/auth/callback"
echo "and ensure UPSTREAM_CLIENT_ID / UPSTREAM_CLIENT_SECRET are in .env"
