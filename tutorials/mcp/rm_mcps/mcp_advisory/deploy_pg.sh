#!/bin/bash
set -e

# Deploys the RM Agent Advisory MCP to Azure exactly like mcp_sql_demo:
# PostgreSQL Flexible Server (seeded from every sql/*.sql) + ACR + Linux Web App
# running the container. Idempotent: the DB server/database are only created on
# first run; later runs just rebuild and redeploy the image.

# === CONFIGURATION ===
SUBSCRIPTION="${SUBSCRIPTION:-698f3b43-ccb0-4f97-9e10-2ca89a7782cf}"
RG="${RG:-rg-lab-demo-001-rm-agent-mcp}"
LOCATION="${LOCATION:-westeurope}"
APP="rm-advisory-mcp"
ACR="rmmcpsacr"               # shared registry for all RM MCPs
PG_SERVER="${PG_SERVER:-rm-mcps-pg-db}"     # shared Postgres server for all RM MCPs
PG_ADMIN_USER="pgadmin"
PG_DB="rmmcps"                # shared DB; Advisory tables are namespaced

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

# === RESOURCE GROUP (idempotent) — reuse if it already exists (it may live in a
# different region than $LOCATION, e.g. a pre-provisioned lab RG); only create when missing. ===
az group show -n "$RG" 1>/dev/null 2>&1 || az group create -n "$RG" -l "$LOCATION" 1>/dev/null

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

# === CREATE DATABASE (idempotent) — show-or-create. NOTE: the db name flag is
# -n/--name, NOT --database-name (current az CLI rejects the latter). ===
echo "[3/8] Creating database..."
az postgres flexible-server db show --server-name "$PG_SERVER" -g "$RG" -n "$PG_DB" &>/dev/null \
  || az postgres flexible-server db create --server-name "$PG_SERVER" -g "$RG" -n "$PG_DB" 1>/dev/null

# === FIREWALL RULE (allow Azure Web Apps + psql; idempotent) — flags are
# --server-name (the server) and --name (the rule). Current az CLI rejects the
# --name/--rule-name combo used elsewhere, and create updates an existing rule,
# so this is safe to re-run. NOT masked: without this rule the Web Apps cannot
# reach Postgres, so a failure here must fail the deploy. ===
echo "[4/8] Firewall rule..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RG" --server-name "$PG_SERVER" \
  --name AllowAll \
  --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255 1>/dev/null

# === SEED ADVISORY DATA (required; idempotent) — every sql/*.sql, one per domain ===
echo "[5/8] Seeding Advisory tables (sql/*.sql)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/src/mcp_advisory/sql"
if ! ls "${SQL_DIR}"/*.sql >/dev/null 2>&1; then
  echo "ERROR: no SQL seed files found in: $SQL_DIR"
  exit 1
fi
if ! command -v psql &>/dev/null; then
  echo "ERROR: psql is required to seed the database. Install PostgreSQL client (e.g. brew install libpq && brew link --force libpq) and ensure psql is on PATH."
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
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8003
az webapp config set -n "$APP" -g "$RG" --always-on true

# === APP ENVIRONMENT VARIABLES (Postgres) ===
echo "[8/8] App settings..."
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
echo ""
echo "Advisory serves bank-wide / portfolio data with NO per-user auth required, so"
echo "the server runs open by default. To enable Zitadel OAuth (same as mcp_sql_demo),"
echo "set these app settings and add the redirect URI in Zitadel:"
echo "  az webapp config appsettings set -n $APP -g $RG --settings \\"
echo "    ZITADEL_URL=https://id.unique.app \\"
echo "    UPSTREAM_CLIENT_ID=<zitadel-client-id> \\"
echo "    UPSTREAM_CLIENT_SECRET=<zitadel-client-secret>"
echo ""
echo "PostgreSQL server is not recreated on subsequent runs; only the app image is rebuilt and redeployed."
