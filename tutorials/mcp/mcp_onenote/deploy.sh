#!/bin/bash
set -e

# === CONFIGURATION ===
SUBSCRIPTION="698f3b43-ccb0-4f97-9e10-2ca89a7782cf"
RG="rg-lab-demo-001-onenote-mcp"
LOCATION="westeurope"
APP="onenote-mcp-app"
ACR="onenotemcpacr"

#az login

# === SET SUBSCRIPTION  ===
az account set --subscription $SUBSCRIPTION

# === CREATE ACR (persists, ~$0.17/day, stores your docker images) ===
az acr create -n $ACR -g $RG --sku Basic --admin-enabled true 2>/dev/null || echo "ACR exists"

# === BUILD IMAGE IN AZURE ===
az acr build -t $APP:latest -r $ACR .

# === CREATE APP SERVICE PLAN (the "server", B1 ~$13/month) ===
az appservice plan create -n "${APP}-plan" -g $RG --is-linux --sku B1 2>/dev/null || echo "Plan exists"

# === CREATE WEB APP (or update if exists) ===
az webapp create -n $APP -g $RG -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" 2>/dev/null || \
az webapp config container set -n $APP -g $RG \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS (lets web app pull from ACR) ===
az webapp config container set -n $APP -g $RG \
  --container-registry-url "https://${ACR}.azurecr.io"

# === SET PORT (your app listens on 3000) ===
az webapp config appsettings set -n $APP -g $RG --settings WEBSITES_PORT=3000

# === ENABLE ALWAYS ON (prevents idle timeout, included in B1) ===
az webapp config set -n $APP -g $RG --always-on true

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "SSE endpoint: https://${APP}.azurewebsites.net/sse"