#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
  echo "Loaded .env"
fi

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-$(az account show --query id -o tsv)}"
RG="${RG:-rg-lab-demo-001-risk-db-mcp}"
LOCATION="${LOCATION:-swedencentral}"
APP="${APP:-risk-db-mcp-app}"
ACR="${ACR:-riskdbmcpacr}"
PG_SERVER="${PG_SERVER:-risk-db-mcp-pg-db}"
PG_ADMIN_USER="${PG_ADMIN_USER:-pgadmin}"
PG_DB="${PG_DB:-riskdb}"

if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "PostgreSQL admin password is required. Set PG_ADMIN_PASSWORD in .env or enter it now."
  read -rs PG_ADMIN_PASSWORD
  echo ""
fi
if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "ERROR: PG_ADMIN_PASSWORD is required to create/configure the database."
  exit 1
fi

if [ -z "${UPSTREAM_CLIENT_ID}" ] || [ -z "${UPSTREAM_CLIENT_SECRET}" ]; then
  echo "WARNING: UPSTREAM_CLIENT_ID and/or UPSTREAM_CLIENT_SECRET not set."
  echo "  OAuth will not work until they are configured. Add them to .env and re-run."
fi

echo "[1/9] Setting subscription..."
az account set --subscription "$SUBSCRIPTION"

echo "[2/9] PostgreSQL Flexible Server (first run may take several minutes)..."
if az postgres flexible-server show -n "$PG_SERVER" -g "$RG" &>/dev/null; then
  echo "  Server exists, skipping create."
else
  az postgres flexible-server create \
    --name "$PG_SERVER" --resource-group "$RG" --location "$LOCATION" \
    --admin-user "$PG_ADMIN_USER" --admin-password "$PG_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms --tier Burstable \
    --storage-size 32 --version 16 \
    --yes
fi

echo "[3/9] Database..."
az postgres flexible-server db create \
  --server-name "$PG_SERVER" --resource-group "$RG" \
  --database-name "$PG_DB" 2>/dev/null || echo "  Database exists."

echo "[4/9] Firewall (demo: allow all IPs)..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RG" --name "$PG_SERVER" \
  --rule-name AllowAll \
  --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255 \
  2>/dev/null || echo "  Rule exists."

PG_FQDN=$(az postgres flexible-server show -n "$PG_SERVER" -g "$RG" --query fullyQualifiedDomainName -o tsv)
PG_URL="postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_FQDN}:5432/${PG_DB}?sslmode=require"

echo "[5/9] ACR..."
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || echo "ACR exists"
az acr build -t "$APP:latest" -r "$ACR" .

echo "[6/9] App Service plan + Web App..."
az appservice plan create -n "${APP}-plan" -g "$RG" --is-linux --sku B1 2>/dev/null || echo "Plan exists"
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" 2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io"

echo "[7/9] Always on..."
az webapp config set -n "$APP" -g "$RG" --always-on true

echo "[8/9] App settings (Postgres, OAuth, ports)..."
az webapp config appsettings set -n "$APP" -g "$RG" --settings \
  WEBSITES_PORT=8002 \
  PORT=8002 \
  PGHOST="$PG_FQDN" \
  PGPORT=5432 \
  PGDATABASE="$PG_DB" \
  PGUSER="$PG_ADMIN_USER" \
  PGPASSWORD="$PG_ADMIN_PASSWORD" \
  PG_CLIENT_STORAGE_URL="$PG_URL" \
  BASE_URL_ENV="https://${APP}.azurewebsites.net" \
  ZITADEL_URL="${ZITADEL_URL:-https://id.unique.app}" \
  UPSTREAM_CLIENT_ID="${UPSTREAM_CLIENT_ID:-}" \
  UPSTREAM_CLIENT_SECRET="${UPSTREAM_CLIENT_SECRET:-}" \
  PG_SSLMODE=require

echo "[9/9] Done."

echo ""
echo "App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo "Postgres host: ${PG_FQDN}  database: ${PG_DB}  user: ${PG_ADMIN_USER}"
echo ""
if [ -n "${UPSTREAM_CLIENT_ID}" ]; then
  echo "Zitadel OAuth: configured (client ID ${UPSTREAM_CLIENT_ID})"
else
  echo "WARNING: UPSTREAM_CLIENT_ID / UPSTREAM_CLIENT_SECRET not set. Add to .env and re-run."
fi
echo ""
echo "Postgres is not recreated on later runs; only the container image is rebuilt."
