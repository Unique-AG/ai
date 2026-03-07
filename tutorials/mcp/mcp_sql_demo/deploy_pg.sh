#!/bin/bash
set -e

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-sql-mcp}"
LOCATION="${LOCATION:-westeurope}"
APP="sql-mcp-demo-pg"
ACR="sqlmcpdemopgacr"
PG_SERVER="sql-mcp-demo-pg-db"
PG_ADMIN_USER="pgadmin"
PG_DB="mcpdb"

# PG admin password required (set PG_ADMIN_PASSWORD in env or enter when prompted)
if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "PostgreSQL admin password is required. Set PG_ADMIN_PASSWORD (env) or enter it now."
  read -rs PG_ADMIN_PASSWORD
  echo ""
fi
if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "ERROR: PG_ADMIN_PASSWORD is required. Without it the database cannot be created or configured."
  exit 1
fi

# === SET SUBSCRIPTION ===
echo "[1/8] Setting subscription..."
az account set --subscription "$SUBSCRIPTION"

# === CREATE POSTGRESQL FLEXIBLE SERVER (idempotent; not recreated if exists) ===
echo "[2/8] PostgreSQL Flexible Server (this can take 5-15 min on first run)..."
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

# === CREATE DATABASE (idempotent) ===
echo "[3/8] Creating database..."
az postgres flexible-server db create \
  --server-name "$PG_SERVER" --resource-group "$RG" \
  --database-name "$PG_DB" 2>/dev/null || echo "  Database exists."

# === FIREWALL RULE (allow Web App and psql; idempotent) ===
echo "[4/8] Firewall rule..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RG" --name "$PG_SERVER" \
  --rule-name AllowAll \
  --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255 \
  2>/dev/null || echo "  Rule exists."

# === SEED PM DATA (required; idempotent) ===
echo "[5/8] Seeding pm_positions..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_FILE="${SCRIPT_DIR}/src/mcp_sql_demo/sql/create_table_postgres.sql"
if [ ! -f "$SQL_FILE" ]; then
  echo "ERROR: SQL seed file not found: $SQL_FILE"
  exit 1
fi
if ! command -v psql &>/dev/null; then
  echo "ERROR: psql is required to seed the database. Install PostgreSQL client (e.g. brew install libpq && brew link --force libpq) and ensure psql is on PATH."
  exit 1
fi
PG_FQDN=$(az postgres flexible-server show -n "$PG_SERVER" -g "$RG" --query fullyQualifiedDomainName -o tsv)
export PGPASSWORD="${PG_ADMIN_PASSWORD}"
if ! psql "postgresql://${PG_ADMIN_USER}@${PG_FQDN}:5432/${PG_DB}?sslmode=require" -f "$SQL_FILE"; then
  unset PGPASSWORD
  echo "ERROR: Failed to seed pm_positions table."
  exit 1
fi
unset PGPASSWORD

# === CREATE ACR (idempotent) ===
echo "[6/8] ACR and build..."
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || true
az acr build -t "${APP}:latest" -r "$ACR" .

# === CREATE APP SERVICE PLAN + WEB APP ===
echo "[7/8] Web App..."
az appservice plan create -n "${APP}-plan" -g "$RG" --is-linux --sku B1 2>/dev/null || true

# === CREATE WEB APP (or update if exists) ===
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" 2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"

# === CONFIGURE ACR ACCESS ===
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io"

# === SET PORT AND ALWAYS ON ===
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8002
az webapp config set -n "$APP" -g "$RG" --always-on true

# === APP ENVIRONMENT VARIABLES (Postgres + client_storage URL) ===
echo "[8/8] App settings..."
PG_URL="postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_FQDN}:5432/${PG_DB}?sslmode=require"
az webapp config appsettings set -n "$APP" -g "$RG" --settings \
  DB_TYPE=postgres \
  PGHOST="$PG_FQDN" \
  PGPORT=5432 \
  PGDATABASE="$PG_DB" \
  PGUSER="$PG_ADMIN_USER" \
  PGPASSWORD="$PG_ADMIN_PASSWORD" \
  BASE_URL_ENV="https://${APP}.azurewebsites.net" \
  PG_CLIENT_STORAGE_URL="$PG_URL" \
  ZITADEL_URL="https://id.unique.app" \
  UNIQUE_SDK_API_BASE="https://gateway.unique.app/public/chat-gen2"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo ""
echo "IMPORTANT: Set these required secrets via Azure Portal:"
echo "  UNIQUE_SDK_API_KEY, UNIQUE_SDK_APP_ID, COMPANY_ID, USER_ID"
echo "  Without COMPANY_ID and USER_ID the gateway returns 401 for ChatCompletion."
echo "  Example: az webapp config appsettings set -n $APP -g $RG --settings UNIQUE_SDK_API_KEY=... UNIQUE_SDK_APP_ID=... COMPANY_ID=... USER_ID=..."
echo ""
echo "PostgreSQL server is not recreated on subsequent runs; only the app image is rebuilt and redeployed."
