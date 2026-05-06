#!/bin/bash
# ============================================================================
# MCP Search - Azure Deployment Verification Script
# ============================================================================
# This script comprehensively verifies that Terraform has properly deployed
# the MCP Search application to Azure by checking:
# - Terraform state
# - Azure resource existence
# - Container instance status
# - Health endpoints
# - Log Analytics connectivity
# - DNS resolution
# - Key Vault secrets
# - Container Registry accessibility
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Counters for results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
    WARNINGS=$((WARNINGS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed"
        return 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        return 1
    fi
    
    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first"
        return 1
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        log_warn "curl is not installed (needed for endpoint testing)"
    fi
    
    # Check jq (optional but helpful)
    if ! command -v jq &> /dev/null; then
        log_warn "jq is not installed (some checks may be less detailed)"
    fi
    
    log_success "All prerequisites satisfied"
    return 0
}

verify_terraform_state() {
    log_info ""
    log_info "=========================================="
    log_info "1. Verifying Terraform State"
    log_info "=========================================="
    
    cd "$SCRIPT_DIR"
    
    # Check if terraform is initialized
    if [ ! -d ".terraform" ]; then
        log_error "Terraform not initialized. Run 'terraform init' first"
        return 1
    fi
    
    log_success "Terraform initialized"
    
    # Check if state file exists (local or remote)
    if terraform state list &> /dev/null; then
        log_success "Terraform state accessible"
        
        # Count resources in state
        RESOURCE_COUNT=$(terraform state list 2>/dev/null | wc -l | tr -d ' ')
        log_info "Found $RESOURCE_COUNT resources in Terraform state"
        
        if [ "$RESOURCE_COUNT" -eq 0 ]; then
            log_error "No resources found in Terraform state"
            return 1
        fi
    else
        log_error "Cannot access Terraform state"
        return 1
    fi
    
    return 0
}

verify_terraform_outputs() {
    log_info ""
    log_info "=========================================="
    log_info "2. Verifying Terraform Outputs"
    log_info "=========================================="
    
    cd "$SCRIPT_DIR"
    
    # Required outputs
    REQUIRED_OUTPUTS=(
        "resource_group_name"
        "acr_name"
        "key_vault_name"
        "storage_account_name"
        "aci_name"
        "aci_fqdn"
        "aci_ip_address"
    )
    
    MISSING_OUTPUTS=()
    
    for output in "${REQUIRED_OUTPUTS[@]}"; do
        if terraform output -raw "$output" &> /dev/null; then
            VALUE=$(terraform output -raw "$output" 2>/dev/null)
            if [ -n "$VALUE" ] && [ "$VALUE" != "null" ]; then
                log_success "Output '$output' exists: ${VALUE:0:50}..."
            else
                log_error "Output '$output' is empty or null"
                MISSING_OUTPUTS+=("$output")
            fi
        else
            log_error "Output '$output' not found"
            MISSING_OUTPUTS+=("$output")
        fi
    done
    
    if [ ${#MISSING_OUTPUTS[@]} -gt 0 ]; then
        log_error "Missing outputs: ${MISSING_OUTPUTS[*]}"
        return 1
    fi
    
    # Get outputs for later checks
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null)
    ACR_NAME=$(terraform output -raw acr_name 2>/dev/null)
    KEY_VAULT_NAME=$(terraform output -raw key_vault_name 2>/dev/null)
    STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name 2>/dev/null)
    ACI_NAME=$(terraform output -raw aci_name 2>/dev/null)
    ACI_FQDN=$(terraform output -raw aci_fqdn 2>/dev/null)
    ACI_IP=$(terraform output -raw aci_ip_address 2>/dev/null)
    
    return 0
}

verify_azure_resources() {
    log_info ""
    log_info "=========================================="
    log_info "3. Verifying Azure Resources Exist"
    log_info "=========================================="
    
    if [ -z "$RESOURCE_GROUP" ]; then
        log_error "Cannot verify Azure resources - resource group name not available"
        return 1
    fi
    
    # Check resource group exists
    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        log_success "Resource group '$RESOURCE_GROUP' exists"
    else
        log_error "Resource group '$RESOURCE_GROUP' does not exist"
        return 1
    fi
    
    # Check Container Registry
    if [ -n "$ACR_NAME" ]; then
        if az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Container Registry '$ACR_NAME' exists"
        else
            log_error "Container Registry '$ACR_NAME' does not exist"
        fi
    fi
    
    # Check Key Vault
    if [ -n "$KEY_VAULT_NAME" ]; then
        if az keyvault show --name "$KEY_VAULT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Key Vault '$KEY_VAULT_NAME' exists"
        else
            log_error "Key Vault '$KEY_VAULT_NAME' does not exist"
        fi
    fi
    
    # Check Storage Account
    if [ -n "$STORAGE_ACCOUNT_NAME" ]; then
        if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Storage Account '$STORAGE_ACCOUNT_NAME' exists"
        else
            log_error "Storage Account '$STORAGE_ACCOUNT_NAME' does not exist"
        fi
    fi
    
    # Check Container Instance
    if [ -n "$ACI_NAME" ]; then
        if az container show --name "$ACI_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Container Instance '$ACI_NAME' exists"
        else
            log_error "Container Instance '$ACI_NAME' does not exist"
            return 1
        fi
    fi
    
    # Check Log Analytics Workspace
    LAW_NAME=$(terraform output -raw log_analytics_workspace_name 2>/dev/null || echo "")
    if [ -n "$LAW_NAME" ]; then
        if az monitor log-analytics workspace show --workspace-name "$LAW_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
            log_success "Log Analytics Workspace '$LAW_NAME' exists"
        else
            log_warn "Log Analytics Workspace '$LAW_NAME' not found (may still be deploying)"
        fi
    fi
    
    return 0
}

verify_container_status() {
    log_info ""
    log_info "=========================================="
    log_info "4. Verifying Container Instance Status"
    log_info "=========================================="
    
    if [ -z "$ACI_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_error "Cannot verify container status - ACI details not available"
        return 1
    fi
    
    # Get container group state
    STATE=$(az container show \
        --name "$ACI_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "instanceView.state" \
        --output tsv 2>/dev/null || echo "")
    
    if [ -z "$STATE" ]; then
        log_error "Cannot retrieve container state"
        return 1
    fi
    
    if [ "$STATE" == "Running" ]; then
        log_success "Container group is Running"
    else
        log_error "Container group state is '$STATE' (expected: Running)"
    fi
    
    # Check individual containers
    CONTAINERS=$(az container show \
        --name "$ACI_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "containers[*].{name:name, state:instanceView.currentState.state, restartCount:instanceView.restartCount}" \
        --output json 2>/dev/null || echo "[]")
    
    if [ "$CONTAINERS" != "[]" ]; then
        # Dynamically detect the MCP search container name (it's var.base_name, not hardcoded)
        # Try to get it from Terraform, or detect from container list (non-caddy container)
        MCP_CONTAINER_NAME=$(terraform output -raw base_name 2>/dev/null || echo "")
        
        if [ -z "$MCP_CONTAINER_NAME" ]; then
            # Try to detect from container list - find container that's not "caddy"
            if command -v jq &> /dev/null; then
                MCP_CONTAINER_NAME=$(echo "$CONTAINERS" | jq -r '.[] | select(.name != "caddy") | .name' 2>/dev/null | head -1 || echo "")
            else
                # Fallback: try common names
                if echo "$CONTAINERS" | grep -q '"name":"search-mcp"'; then
                    MCP_CONTAINER_NAME="search-mcp"
                elif echo "$CONTAINERS" | grep -q '"name":"mcp-search"'; then
                    MCP_CONTAINER_NAME="mcp-search"
                fi
            fi
        fi
        
        if [ -z "$MCP_CONTAINER_NAME" ]; then
            log_warn "Could not determine MCP container name, trying 'mcp-search'"
            MCP_CONTAINER_NAME="mcp-search"
        fi
        
        log_info "Checking MCP container: $MCP_CONTAINER_NAME"
        
        # Parse container details (with or without jq)
        if command -v jq &> /dev/null; then
            # Use jq if available
            MCP_SEARCH_STATE=$(echo "$CONTAINERS" | jq -r ".[] | select(.name==\"$MCP_CONTAINER_NAME\") | .state" 2>/dev/null || echo "")
            MCP_SEARCH_RESTARTS=$(echo "$CONTAINERS" | jq -r ".[] | select(.name==\"$MCP_CONTAINER_NAME\") | .restartCount" 2>/dev/null || echo "0")
            CADDY_STATE=$(echo "$CONTAINERS" | jq -r '.[] | select(.name=="caddy") | .state' 2>/dev/null || echo "")
            CADDY_RESTARTS=$(echo "$CONTAINERS" | jq -r '.[] | select(.name=="caddy") | .restartCount' 2>/dev/null || echo "0")
        else
            # Fallback: use grep/awk for basic parsing
            MCP_SEARCH_STATE=$(echo "$CONTAINERS" | grep -o "\"name\":\"$MCP_CONTAINER_NAME\"[^}]*\"state\":\"[^\"]*" | grep -o "\"state\":\"[^\"]*" | cut -d'"' -f4 || echo "")
            MCP_SEARCH_RESTARTS=$(echo "$CONTAINERS" | grep -o "\"name\":\"$MCP_CONTAINER_NAME\"[^}]*\"restartCount\":[0-9]*" | grep -o "\"restartCount\":[0-9]*" | cut -d':' -f2 || echo "0")
            CADDY_STATE=$(echo "$CONTAINERS" | grep -o '"name":"caddy"[^}]*"state":"[^"]*' | grep -o '"state":"[^"]*' | cut -d'"' -f4 || echo "")
            CADDY_RESTARTS=$(echo "$CONTAINERS" | grep -o '"name":"caddy"[^}]*"restartCount":[0-9]*' | grep -o '"restartCount":[0-9]*' | cut -d':' -f2 || echo "0")
        fi
        
        # Check MCP search container
        if [ -n "$MCP_SEARCH_STATE" ]; then
            if [ "$MCP_SEARCH_STATE" == "Running" ]; then
                log_success "Container '$MCP_CONTAINER_NAME' is Running"
            else
                log_error "Container '$MCP_CONTAINER_NAME' state is '$MCP_SEARCH_STATE' (expected: Running)"
            fi
            
            if [ -n "$MCP_SEARCH_RESTARTS" ] && [ "$MCP_SEARCH_RESTARTS" -gt 5 ] 2>/dev/null; then
                log_warn "Container '$MCP_CONTAINER_NAME' has restarted $MCP_SEARCH_RESTARTS times (may indicate issues)"
            elif [ -n "$MCP_SEARCH_RESTARTS" ] && [ "$MCP_SEARCH_RESTARTS" -gt 0 ] 2>/dev/null; then
                log_info "Container '$MCP_CONTAINER_NAME' has restarted $MCP_SEARCH_RESTARTS times"
            fi
        else
            log_error "Container '$MCP_CONTAINER_NAME' not found in container group"
            log_info "Available containers:"
            if command -v jq &> /dev/null; then
                echo "$CONTAINERS" | jq -r '.[] | "  - \(.name) (\(.state))"' 2>/dev/null || echo "$CONTAINERS"
            else
                echo "$CONTAINERS"
            fi
        fi
        
        # Additional check: if container is Running but endpoints don't work, warn about potential app crash
        if [ "$MCP_SEARCH_STATE" == "Running" ]; then
            log_info "Container '$MCP_CONTAINER_NAME' is running - checking if application is listening..."
            # Note: We can't easily check port connectivity from outside, but we'll test endpoints later
        fi
        
        # Check caddy container
        if [ -n "$CADDY_STATE" ]; then
            if [ "$CADDY_STATE" == "Running" ]; then
                log_success "Container 'caddy' is Running"
            else
                log_error "Container 'caddy' state is '$CADDY_STATE' (expected: Running)"
            fi
            
            if [ -n "$CADDY_RESTARTS" ] && [ "$CADDY_RESTARTS" -gt 5 ] 2>/dev/null; then
                log_warn "Container 'caddy' has restarted $CADDY_RESTARTS times (may indicate issues)"
            fi
        else
            log_error "Container 'caddy' not found in container group"
        fi
    else
        log_error "Cannot retrieve container details"
        return 1
    fi
    
    return 0
}

verify_health_endpoints() {
    log_info ""
    log_info "=========================================="
    log_info "5. Verifying Health Endpoints"
    log_info "=========================================="
    
    if ! command -v curl &> /dev/null; then
        log_warn "curl not available - skipping endpoint tests"
        return 0
    fi
    
    if [ -z "$ACI_FQDN" ] && [ -z "$ACI_IP" ]; then
        log_error "Cannot test endpoints - no FQDN or IP available"
        return 1
    fi
    
    # Get the MCP container name for diagnostics
    MCP_CONTAINER_NAME=$(terraform output -raw base_name 2>/dev/null || echo "search-mcp")
    if [ -z "$MCP_CONTAINER_NAME" ]; then
        MCP_CONTAINER_NAME="search-mcp"
    fi
    
    # Test via FQDN (HTTPS - Caddy serves HTTPS by default)
    if [ -n "$ACI_FQDN" ]; then
        log_info "Testing endpoints via FQDN: $ACI_FQDN"
        
        # Test root endpoint via HTTPS (Caddy serves HTTPS)
        if curl -s -f -m 10 -k "https://${ACI_FQDN}/" &> /dev/null; then
            RESPONSE=$(curl -s -m 10 -k "https://${ACI_FQDN}/" 2>/dev/null || echo "")
            if echo "$RESPONSE" | grep -q "running"; then
                log_success "Root endpoint (/) is responding correctly"
            else
                log_warn "Root endpoint (/) responded but content unexpected: $RESPONSE"
            fi
        else
            # Fallback to HTTP if HTTPS fails
            if curl -s -f -m 10 "http://${ACI_FQDN}/" &> /dev/null; then
                RESPONSE=$(curl -s -m 10 "http://${ACI_FQDN}/" 2>/dev/null || echo "")
                if echo "$RESPONSE" | grep -q "running"; then
                    log_success "Root endpoint (/) is responding correctly (HTTP)"
                else
                    log_warn "Root endpoint (/) responded but content unexpected: $RESPONSE"
                fi
            else
                log_error "Root endpoint (/) is not responding"
            fi
        fi
        
        # Test health endpoint via HTTPS (Caddy serves HTTPS)
        if curl -s -f -m 10 -k "https://${ACI_FQDN}/health" &> /dev/null; then
            RESPONSE=$(curl -s -m 10 -k "https://${ACI_FQDN}/health" 2>/dev/null || echo "")
            if echo "$RESPONSE" | grep -q "healthy\|status"; then
                log_success "Health endpoint (/health via Caddy) is responding"
            else
                log_warn "Health endpoint responded but content unexpected: $RESPONSE"
            fi
        else
            # Fallback to HTTP if HTTPS fails
            if curl -s -f -m 10 "http://${ACI_FQDN}/health" &> /dev/null; then
                RESPONSE=$(curl -s -m 10 "http://${ACI_FQDN}/health" 2>/dev/null || echo "")
                if echo "$RESPONSE" | grep -q "healthy\|status"; then
                    log_success "Health endpoint (/health via Caddy) is responding (HTTP)"
                else
                    log_warn "Health endpoint responded but content unexpected: $RESPONSE"
                fi
            else
                log_error "Health endpoint (/health via Caddy) is not responding"
            fi
        fi
        
        # Note: Port 8003 is not exposed externally (only accessible from within container group)
        # Caddy proxies requests from port 80/443 to the container on port 8003 internally
        log_info "Note: Direct container access on port 8003 is not exposed externally (by design)"
        log_info "      Caddy proxies requests from port 443 to the container internally"
    fi
    
    # Test via IP if FQDN failed
    if [ -n "$ACI_IP" ] && [ -z "$ACI_FQDN" ]; then
        log_info "Testing endpoints via IP: $ACI_IP"
        
        # Try HTTPS first, then HTTP
        if curl -s -f -m 10 -k "https://${ACI_IP}/health" &> /dev/null; then
            log_success "Health endpoint is responding via IP (HTTPS)"
        elif curl -s -f -m 10 "http://${ACI_IP}/health" &> /dev/null; then
            log_success "Health endpoint is responding via IP (HTTP)"
        else
            log_error "Health endpoint is not responding via IP"
        fi
    fi
    
    # Test domain if configured
    DOMAIN_NAME=$(terraform output -raw application_url 2>/dev/null | sed 's|https\?://||' || echo "")
    if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "null" ]; then
        log_info "Testing domain: $DOMAIN_NAME"
        
        # Check DNS resolution
        if nslookup "$DOMAIN_NAME" &> /dev/null; then
            log_success "Domain '$DOMAIN_NAME' resolves via DNS"
            
            # Test HTTPS endpoint
            if curl -s -f -m 10 -k "https://${DOMAIN_NAME}/health" &> /dev/null; then
                log_success "HTTPS health endpoint is responding"
            else
                log_warn "HTTPS health endpoint not responding (certificate may still be provisioning)"
            fi
        else
            log_warn "Domain '$DOMAIN_NAME' does not resolve (DNS may not be configured)"
        fi
    fi
    
    return 0
}

verify_key_vault_secrets() {
    log_info ""
    log_info "=========================================="
    log_info "6. Verifying Key Vault Secrets"
    log_info "=========================================="
    
    if [ -z "$KEY_VAULT_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_warn "Cannot verify Key Vault secrets - details not available"
        return 0
    fi
    
    # Expected secrets
    EXPECTED_SECRETS=(
        "unique-app-key"
        "unique-app-id"
        "unique-api-base-url"
        "unique-auth-company-id"
        "unique-auth-user-id"
        "unique-app-endpoint"
        "unique-app-endpoint-secret"
        "zitadel-base-url"
        "zitadel-client-id"
        "zitadel-client-secret"
        "acr-password"
    )
    
    for secret in "${EXPECTED_SECRETS[@]}"; do
        if az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "$secret" &> /dev/null; then
            log_success "Secret '$secret' exists in Key Vault"
        else
            log_warn "Secret '$secret' not found in Key Vault (may be expected)"
        fi
    done
    
    return 0
}

verify_container_registry() {
    log_info ""
    log_info "=========================================="
    log_info "7. Verifying Container Registry"
    log_info "=========================================="
    
    if [ -z "$ACR_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_warn "Cannot verify Container Registry - details not available"
        return 0
    fi
    
    # Check if we can login
    if az acr login --name "$ACR_NAME" &> /dev/null; then
        log_success "Can authenticate to Container Registry"
    else
        log_warn "Cannot authenticate to Container Registry (may need permissions)"
    fi
    
    # Check if mcp-search image exists
    if az acr repository show-tags --name "$ACR_NAME" --repository mcp-search &> /dev/null; then
        TAGS=$(az acr repository show-tags --name "$ACR_NAME" --repository mcp-search --output tsv 2>/dev/null | wc -l | tr -d ' ')
        if [ "$TAGS" -gt 0 ]; then
            log_success "mcp-search image exists in registry ($TAGS tag(s))"
        else
            log_warn "mcp-search repository exists but has no tags"
        fi
    else
        log_warn "mcp-search image not found in registry (may need to build/push)"
    fi
    
    return 0
}



print_summary() {
    log_info ""
    log_info "=========================================="
    log_info "Verification Summary"
    log_info "=========================================="
    echo ""
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        if [ $WARNINGS -eq 0 ]; then
            echo -e "${GREEN}✓ All checks passed! Deployment appears to be successful.${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ Deployment is functional but has some warnings.${NC}"
            return 0
        fi
    else
        echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
        echo ""
        echo "Common issues and solutions:"
        echo "  - Containers not running: Check logs with './deploy.sh logs'"
        echo "  - Endpoints not responding: Wait a few minutes for containers to start"
        echo "  - Missing resources: Run 'terraform apply' to create them"
        echo "  - DNS issues: Configure DNS records as shown in 'terraform output dns_configuration'"
        return 1
    fi
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "MCP Search - Azure Deployment Verification"
    echo "=========================================="
    echo ""
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Run verification checks
    verify_terraform_state || true
    verify_terraform_outputs || true
    verify_azure_resources || true
    verify_container_status || true
    verify_health_endpoints || true
    verify_key_vault_secrets || true
    verify_container_registry || true
    
    # Print summary
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
