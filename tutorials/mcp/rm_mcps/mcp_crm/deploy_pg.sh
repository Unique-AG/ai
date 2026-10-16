#!/bin/bash
set -e

# Deploys the RM Agent CRM MCP to Azure exactly like mcp_sql_demo / mcp_advisory:
# it SHARES the Advisory server's PostgreSQL Flexible Server + ACR (created by
# mcp_advisory/deploy_pg.sh) and adds its own Linux Web App. Idempotent.

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-rm-agent-mcp}"
LOCATION="${LOCATION:-westeurope}"
APP="rm-crm-mcp"
ACR="rmmcpsacr"               # shared registry for all RM MCPs
PG_SERVER="${PG_SERVER:-rm-mcps-pg-db}"     # shared Postgres server for all RM MCPs
PG_ADMIN_USER="pgadmin"
PG_DB="rmmcps"                # shared DB; CRM tables are namespaced

if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "PostgreSQL admin password is required. Set PG_ADMIN_PASSWORD (env) or enter it now."
  read -rs PG_ADMIN_PASSWORD
  echo ""
fi
if [ -z "${PG_ADMIN_PASSWORD}" ]; then
  echo "ERROR: PG_ADMIN_PASSWORD is required (must match the shared rm-mcps-pg-db admin password)."
  exit 1
fi

echo "[1/7] Setting subscription..."
az account set --subscription "$SUBSCRIPTION"

# The shared Postgres server / database / ACR are created by mcp_advisory/deploy_pg.sh.
# Verify the server exists so CRM doesn't try to create infra it can't.
echo "[2/7] Checking shared Postgres server..."
if ! az postgres flexible-server show -n "$PG_SERVER" -g "$RG" &>/dev/null; then
  echo "ERROR: shared server $PG_SERVER not found in $RG. Run mcp_advisory/deploy_pg.sh first."
  exit 1
fi
# Shared DB is normally created by mcp_advisory; create it here too (idempotent,
# show-or-create) in case CRM is deployed first. The db name flag is -n/--name —
# current az CLI rejects --database-name.
az postgres flexible-server db show --server-name "$PG_SERVER" -g "$RG" -n "$PG_DB" &>/dev/null \
  || az postgres flexible-server db create --server-name "$PG_SERVER" -g "$RG" -n "$PG_DB" 1>/dev/null

echo "[3/7] Seeding CRM tables (sql/*.sql)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/src/mcp_crm/sql"
if ! command -v psql &>/dev/null; then
  echo "ERROR: psql is required to seed the database (brew install libpq && brew link --force libpq)."
  exit 1
fi
PG_FQDN=$(az postgres flexible-server show -n "$PG_SERVER" -g "$RG" --query fullyQualifiedDomainName -o tsv)
export PGPASSWORD="${PG_ADMIN_PASSWORD}"
for SQL_FILE in "${SQL_DIR}"/*.sql; do
  echo "  -> $(basename "$SQL_FILE")"
  if ! psql "postgresql://${PG_ADMIN_USER}@${PG_FQDN}:5432/${PG_DB}?sslmode=require" -f "$SQL_FILE"; then
    unset PGPASSWORD
    echo "ERROR: Failed to seed from $(basename "$SQL_FILE")."
    exit 1
  fi
done
unset PGPASSWORD

echo "[4/7] ACR build..."
az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true 2>/dev/null || true
az acr build -t "${APP}:latest" -r "$ACR" .

echo "[5/7] App Service plan + Web App..."
az appservice plan create -n "${APP}-plan" -g "$RG" --is-linux --sku B1 2>/dev/null || true
az webapp create -n "$APP" -g "$RG" -p "${APP}-plan" \
  --deployment-container-image-name "${ACR}.azurecr.io/${APP}:latest" 2>/dev/null || \
az webapp config container set -n "$APP" -g "$RG" \
  --container-image-name "${ACR}.azurecr.io/${APP}:latest"
az webapp config container set -n "$APP" -g "$RG" \
  --container-registry-url "https://${ACR}.azurecr.io"

echo "[6/7] Port + always-on..."
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8004
az webapp config set -n "$APP" -g "$RG" --always-on true

echo "[7/7] App settings (Postgres)..."
PG_URL="postgresql://${PG_ADMIN_USER}:${PG_ADMIN_PASSWORD}@${PG_FQDN}:5432/${PG_DB}?sslmode=require"
az webapp config appsettings set -n "$APP" -g "$RG" --settings \
  PGHOST="$PG_FQDN" \
  PGPORT=5432 \
  PGDATABASE="$PG_DB" \
  PGUSER="$PG_ADMIN_USER" \
  PGPASSWORD="$PG_ADMIN_PASSWORD" \
  PG_CLIENT_STORAGE_URL="$PG_URL" \
  BASE_URL_ENV="https://${APP}.azurewebsites.net"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo "To enable Zitadel OAuth, set ZITADEL_URL / UPSTREAM_CLIENT_ID / UPSTREAM_CLIENT_SECRET app settings."
