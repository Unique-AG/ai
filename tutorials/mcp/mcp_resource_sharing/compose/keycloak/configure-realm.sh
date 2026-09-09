#!/usr/bin/env bash
# Post-import Keycloak setup for the compose demo.
#
# Realm JSON cannot express FGAP v1 token-exchange permissions reliably (they
# live on realm-management and reference runtime UUIDs). This script enables
# external→internal exchange from Dex and audience-bound minting for
# resource-producer.
set -euo pipefail

KCADM=/opt/keycloak/bin/kcadm.sh
SERVER="${KEYCLOAK_URL:-http://keycloak:8080}"
REALM=producer
ADMIN="${KEYCLOAK_ADMIN:-admin}"
PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:?KEYCLOAK_ADMIN_PASSWORD is required}"

echo "keycloak-setup: waiting for ${SERVER} ..."
for _ in $(seq 1 90); do
  if ${KCADM} config credentials --server "${SERVER}" --realm master --user "${ADMIN}" --password "${PASSWORD}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

client_uuid() {
  ${KCADM} get clients -r "${REALM}" -q "clientId=$1" --fields id --format csv --noquotes 2>/dev/null | tail -1
}

policy_uuid() {
  local rm_id=$1 name=$2
  ${KCADM} get "clients/${rm_id}/authz/resource-server/policy" -r "${REALM}" \
    -q "name=${name}" --fields id --format csv --noquotes 2>/dev/null | tail -1
}

write_client_policy() {
  local rm_id=$1 alice_id=$2 consumer_id=$3
  local name=consumer-clients-can-exchange-idp
  cat > /tmp/kc-client-policy.json <<JSON
{
  "name": "${name}",
  "type": "client",
  "logic": "POSITIVE",
  "decisionStrategy": "UNANIMOUS",
  "config": {
    "clients": "[\"${alice_id}\",\"${consumer_id}\"]"
  }
}
JSON
  local existing
  existing=$(policy_uuid "${rm_id}" "${name}" || true)
  if [[ -n "${existing}" && "${existing}" != "id" ]]; then
    ${KCADM} update "clients/${rm_id}/authz/resource-server/policy/${existing}" \
      -r "${REALM}" -f /tmp/kc-client-policy.json
  else
    ${KCADM} create "clients/${rm_id}/authz/resource-server/policy" \
      -r "${REALM}" -f /tmp/kc-client-policy.json
  fi
}

write_scope_permission() {
  local rm_id=$1 perm_id=$2 perm_name=$3 resource_name=$4
  cat > /tmp/kc-scope-perm.json <<JSON
{
  "name": "${perm_name}",
  "type": "scope",
  "logic": "POSITIVE",
  "decisionStrategy": "UNANIMOUS",
  "config": {
    "resources": "[\"${resource_name}\"]",
    "scopes": "[\"token-exchange\"]",
    "applyPolicies": "[\"consumer-clients-can-exchange-idp\"]"
  }
}
JSON
  ${KCADM} update "clients/${rm_id}/authz/resource-server/policy/${perm_id}" \
    -r "${REALM}" -f /tmp/kc-scope-perm.json
}

ALICE_ID=$(client_uuid alice-desktop-app)
CONSUMER_ID=$(client_uuid resource-consumer-service)
PRODUCER_ID=$(client_uuid resource-producer)
RM_ID=$(client_uuid realm-management)

if [[ -z "${ALICE_ID}" || -z "${CONSUMER_ID}" || -z "${PRODUCER_ID}" || -z "${RM_ID}" ]]; then
  echo "keycloak-setup: missing expected clients in realm ${REALM}" >&2
  exit 1
fi

echo "keycloak-setup: configuring Dex IdP token validation ..."
${KCADM} update identity-provider/instances/dex -r "${REALM}" \
  -s 'config.jwksUrl=http://dex:5556/keys' \
  -s 'config.userInfoUrl=http://dex:5556/userinfo' \
  -s 'config.disableUserInfo=false' \
  -s 'config.useJwksUrl=true' \
  -s 'config.syncMode=IMPORT'

echo "keycloak-setup: enabling token-exchange permissions ..."
${KCADM} update identity-provider/instances/dex/management/permissions -r "${REALM}" -s enabled=true
${KCADM} update "clients/${PRODUCER_ID}/management/permissions" -r "${REALM}" -s enabled=true

write_client_policy "${RM_ID}" "${ALICE_ID}" "${CONSUMER_ID}"

IDP_PERM_ID=$(policy_uuid "${RM_ID}" "token-exchange.permission.idp.dex-idp")
CLIENT_PERM_ID=$(policy_uuid "${RM_ID}" "token-exchange.permission.client.${PRODUCER_ID}")

if [[ -z "${IDP_PERM_ID}" || -z "${CLIENT_PERM_ID}" ]]; then
  echo "keycloak-setup: token-exchange permissions not found after enabling management permissions" >&2
  exit 1
fi

write_scope_permission "${RM_ID}" "${IDP_PERM_ID}" \
  "token-exchange.permission.idp.dex-idp" "idp.resource.dex-idp"
write_scope_permission "${RM_ID}" "${CLIENT_PERM_ID}" \
  "token-exchange.permission.client.${PRODUCER_ID}" "client.resource.${PRODUCER_ID}"

echo "keycloak-setup: producer realm ready for Dex → Keycloak token exchange."
