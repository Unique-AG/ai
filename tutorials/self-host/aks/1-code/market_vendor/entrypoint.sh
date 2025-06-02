#!/bin/sh
# ============================================================================
# MOCK FILE - SDK DEPLOYMENT EXAMPLE
# ============================================================================
# This is a mock entrypoint script for demonstration purposes only.
# It shows how an SDK assistant container might handle SOPS decryption and
# startup. This file is NOT production-ready and should be adapted to your
# specific security and deployment requirements.
# ============================================================================

set -e

echo "🎬 Starting entrypoint script..."

# Validate required environment variables
if [ -z "$ENCRYPTED_ENV_FILE" ] || [ -z "$DECRYPTED_ENV_FILE_ABSOLUTE" ]; then
    echo "❌ ERROR: Required environment variables are not set."
    echo "ENCRYPTED_ENV_FILE: $ENCRYPTED_ENV_FILE"
    echo "DECRYPTED_ENV_FILE_ABSOLUTE: $DECRYPTED_ENV_FILE_ABSOLUTE" 
    exit 1
fi

# Check if SOPS_AGE_KEY is set
if [ -z "$SOPS_AGE_KEY" ]; then
    echo "❌🔑 ERROR: SOPS_AGE_KEY environment variable is not set."
    exit 1
fi

echo "🔓 Decrypting secrets file..."
if ! sops --decrypt --input-type=dotenv --output-type=dotenv "/code/$ENCRYPTED_ENV_FILE" > "$DECRYPTED_ENV_FILE_ABSOLUTE"; then
    echo "ERROR: Failed to decrypt secrets file"
    echo "ENCRYPTED_ENV_FILE: $ENCRYPTED_ENV_FILE"
    echo "DECRYPTED_ENV_FILE_ABSOLUTE: $DECRYPTED_ENV_FILE_ABSOLUTE" 
    exit 1
fi
echo "🥾 Successfully decrypted secrets to $DECRYPTED_ENV_FILE_ABSOLUTE"

if [ ! -s "$DECRYPTED_ENV_FILE_ABSOLUTE" ]; then
    echo "❌ ERROR: Decrypted env file $DECRYPTED_ENV_FILE_ABSOLUTE is empty."
    exit 1
fi

echo "🔍 Decrypted env keys:"
grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$DECRYPTED_ENV_FILE_ABSOLUTE" | cut -d '=' -f1


# Print API_BASE value from the decrypted file
echo "🔑 API_BASE value from decrypted file:"
grep -E '^API_BASE=' "$DECRYPTED_ENV_FILE_ABSOLUTE" || echo "API_BASE not found in file"

# Source the decrypted environment variables
echo "📥 Loading environment variables from $DECRYPTED_ENV_FILE_ABSOLUTE"
set -a
. "$DECRYPTED_ENV_FILE_ABSOLUTE"
set +a

echo "Starting Gunicorn server..."
echo "API Base: $API_BASE"
echo "App Entry: $APP_ENTRY"
echo "APP ID: $APP_ID"
echo "App Name: $APP_NAME"
echo "Module: $MODULE"
echo "Port: $PORT"

if [ -z "$API_BASE" ] || [ -z "$APP_ENTRY" ] || [ -z "$APP_ID" ] || [ -z "$APP_NAME" ] || [ -z "$MODULE" ] || [ -z "$PORT" ]; then
    echo "❌ ERROR: Required SDK or assistant variables are not set. Check logs above."
    exit 1
fi

# use gunicorn as the entrypoint from CMD
set -x

exec poetry run gunicorn \
  --workers=2 \
  --threads=4 \
  --worker-class=gthread \
  --worker-tmp-dir /dev/shm \
  --bind 0.0.0.0:$PORT \
  $MODULE:$APP_ENTRY

set +x
set +e