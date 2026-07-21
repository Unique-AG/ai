#!/bin/bash
set -e

# === CONFIGURATION ===
# No baked-in defaults: set SUBSCRIPTION/RG/APP/ACR via environment variables
# or a local deploy.env next to this script (gitignored; see deploy.env.example).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/deploy.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$SCRIPT_DIR/deploy.env"; set +a
fi
for var in SUBSCRIPTION RG APP ACR; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: $var is not set. Export it or copy deploy.env.example to" >&2
    echo "       $SCRIPT_DIR/deploy.env and fill in your values." >&2
    exit 1
  fi
done
PLAN="${PLAN:-${APP}-plan}"

# Package root (build context + default env file location), two levels up.
PACKAGE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PACKAGE_DIR"

# === ARGUMENTS ===
# --skip-secrets       don't push app/Zitadel secrets (prints manual command)
# --env-file <path>    extra env file to source secrets from (repeatable);
#                      defaults: unique.env + zitadel.env in the package root
SKIP_SECRETS=false
ENV_FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-secrets) SKIP_SECRETS=true; shift ;;
    --env-file) ENV_FILES+=("$2"); shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
if [[ ${#ENV_FILES[@]} -eq 0 ]]; then
  ENV_FILES=("$PACKAGE_DIR/unique.env" "$PACKAGE_DIR/zitadel.env")
fi

# Secrets pushed to the Web App. UNIQUE_AUTH_USER_ID / UNIQUE_AUTH_COMPANY_ID
# are deliberately NOT in this list: identity must come from the OAuth login,
# never a fixed service user (see README "Identity Resolution").
REQUIRED_SECRET_VARS=(
  UNIQUE_APP_KEY UNIQUE_APP_ID UNIQUE_API_BASE_URL
  ZITADEL_BASE_URL ZITADEL_CLIENT_ID ZITADEL_CLIENT_SECRET
)

load_and_validate_secrets() {
  for f in "${ENV_FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
      echo "ERROR: env file not found: $f (use --env-file or --skip-secrets)" >&2
      exit 1
    fi
    # shellcheck disable=SC1090
    set -a; source "$f"; set +a
  done
  local missing=()
  for var in "${REQUIRED_SECRET_VARS[@]}"; do
    local val="${!var:-}"
    if [[ -z "$val" || "$val" == *"your-"* || "$val" == *"<"* || "$val" == "..." ]]; then
      missing+=("$var")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "ERROR: missing or placeholder values in ${ENV_FILES[*]}: ${missing[*]}" >&2
    echo "Fill them in (see unique.env.example / zitadel.env.example) or pass --skip-secrets." >&2
    exit 1
  fi
}

if [[ "$SKIP_SECRETS" == false ]]; then
  load_and_validate_secrets
fi

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
# Explicit admin credentials: the automatic lookup silently fails on freshly
# created Web Apps, leaving DOCKER_REGISTRY_SERVER_PASSWORD null (image pull
# then fails and the site answers 421).
ACR_USER="$(az acr credential show -n "$ACR" --query username -o tsv)"
ACR_PASS="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"
az webapp config container set -n "$APP" -g "$RG" -o none \
  --container-registry-url "https://${ACR}.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS" \
  --container-image-name "${IMAGE_REF}"

# === SET PORT AND ALWAYS ON ===
echo "[5/6] Port and Always On..."
az webapp config appsettings set -n "$APP" -g "$RG" --settings WEBSITES_PORT=8003 -o none
az webapp config set -n "$APP" -g "$RG" --always-on true -o none

# === APP ENVIRONMENT VARIABLES (non-secret) ===
echo "[6/6] App settings..."
az webapp config appsettings set -n "$APP" -g "$RG" -o none --settings \
  UNIQUE_MCP_LOCAL_BASE_URL="http://0.0.0.0:8003" \
  UNIQUE_MCP_PUBLIC_BASE_URL="https://${APP}.azurewebsites.net" \
  UNIQUE_MCP_FRONTEND_BASE_URL="${UNIQUE_MCP_FRONTEND_BASE_URL:-https://next.qa.unique.app}"

# === APP SECRETS (from local env files, unless --skip-secrets) ===
if [[ "$SKIP_SECRETS" == false ]]; then
  echo "Pushing app secrets from: ${ENV_FILES[*]}"
  SECRET_ARGS=()
  for var in "${REQUIRED_SECRET_VARS[@]}"; do
    SECRET_ARGS+=("${var}=${!var}")
  done
  az webapp config appsettings set -n "$APP" -g "$RG" -o none --settings "${SECRET_ARGS[@]}"
fi

az webapp restart -n "$APP" -g "$RG"

echo ""
echo "Done! App: https://${APP}.azurewebsites.net"
echo "MCP endpoint: https://${APP}.azurewebsites.net/mcp"
echo "Image: ${IMAGE_REF}"
echo ""
if [[ "$SKIP_SECRETS" == true ]]; then
  echo "IMPORTANT: Set app + Zitadel secrets via Azure Portal or CLI:"
  echo "  az webapp config appsettings set -n $APP -g $RG --settings \\"
  echo "    UNIQUE_APP_KEY=... UNIQUE_APP_ID=... UNIQUE_API_BASE_URL=... \\"
  echo "    ZITADEL_BASE_URL=... ZITADEL_CLIENT_ID=... ZITADEL_CLIENT_SECRET=..."
  echo ""
fi
echo "Do NOT set UNIQUE_AUTH_USER_ID / UNIQUE_AUTH_COMPANY_ID on the Web App."
echo "Search identity comes from the logged-in OAuth user (JWT / userinfo)."
echo ""
echo "Fast end-to-end test (OAuth + tool calls):"
echo "  uv run python scripts/debug_auth_client.py --url https://${APP}.azurewebsites.net/mcp"
echo ""
echo "Document deep links use UNIQUE_MCP_FRONTEND_BASE_URL (default https://next.qa.unique.app):"
echo "  {UNIQUE_MCP_FRONTEND_BASE_URL}/knowledge-upload/{scopeId}?file={contentId}"
echo ""
echo "Also register the OAuth redirect URI in Zitadel:"
echo "  https://${APP}.azurewebsites.net/auth/callback"
