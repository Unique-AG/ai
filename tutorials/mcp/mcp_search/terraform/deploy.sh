#!/bin/bash
# ============================================================================
# MCP Search - Azure Deployment Script
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check Azure login
    if ! az account show &> /dev/null; then
        log_error "Not logged in to Azure. Please run 'az login' first."
        exit 1
    fi
    
    log_info "All prerequisites satisfied."
}

init_terraform() {
    log_info "Initializing Terraform..."
    cd "$SCRIPT_DIR"
    terraform init
}

plan_infrastructure() {
    log_info "Planning infrastructure changes..."
    cd "$SCRIPT_DIR"
    terraform plan -out=tfplan || {
        if echo "$?" | grep -q "Error acquiring the state lock"; then
            log_warn "State lock detected. Attempting with -lock=false..."
            terraform plan -lock=false -out=tfplan
        else
            exit 1
        fi
    }
}

apply_infrastructure() {
    log_info "Applying infrastructure changes..."
    cd "$SCRIPT_DIR"
    # Check if plan was created with -lock=false
    if [ -f tfplan ]; then
        terraform apply -lock=false tfplan
    else
        terraform apply tfplan
    fi
}

build_and_push_image() {
    log_info "Building and pushing Docker image..."
    
    # Get ACR details from Terraform output
    cd "$SCRIPT_DIR"
    ACR_NAME=$(terraform output -raw acr_name 2>/dev/null || echo "")
    ACR_LOGIN_SERVER=$(terraform output -raw acr_login_server 2>/dev/null || echo "")
    
    if [ -z "$ACR_NAME" ] || [ -z "$ACR_LOGIN_SERVER" ]; then
        log_error "Could not get ACR details from Terraform. Make sure infrastructure is deployed."
        exit 1
    fi
    
    # Login to ACR
    log_info "Logging in to Azure Container Registry..."
    az acr login --name "$ACR_NAME"
    
    # Build and push using ACR Tasks (builds in Azure)
    # Retry logic for network issues
    log_info "Building image using ACR Tasks..."
    cd "$PROJECT_DIR"
    
    local max_retries=3
    local retry_count=0
    local success=false
    
    while [ $retry_count -lt $max_retries ] && [ "$success" = false ]; do
        if [ $retry_count -gt 0 ]; then
            log_warn "Retry attempt $retry_count of $max_retries..."
            sleep 5
        fi
        
        if az acr build --registry "$ACR_NAME" --image mcp-search:latest .; then
            success=true
            log_info "Image built and pushed successfully to $ACR_LOGIN_SERVER/mcp-search:latest"
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_warn "Build failed, will retry..."
            else
                log_error "Build failed after $max_retries attempts."
                log_info "This might be due to Docker Hub rate limiting or network issues."
                log_info "You can try:"
                log_info "  1. Wait a few minutes and retry: ./deploy.sh build"
                log_info "  2. Build locally and push: docker build -t $ACR_LOGIN_SERVER/mcp-search:latest . && docker push $ACR_LOGIN_SERVER/mcp-search:latest"
                exit 1
            fi
        fi
    done
}

restart_container() {
    log_info "Restarting container instance to pick up new image..."
    
    cd "$SCRIPT_DIR"
    ACI_NAME=$(terraform output -raw aci_name 2>/dev/null || echo "")
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
    
    if [ -z "$ACI_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_error "Could not get ACI details from Terraform."
        exit 1
    fi
    
    az container restart --name "$ACI_NAME" --resource-group "$RESOURCE_GROUP"
    log_info "Container restarted successfully."
}

view_logs() {
    local container_name=""
    local follow=""
    local use_log_analytics=""
    
    # Parse arguments
    shift  # Skip the command name
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--follow)
                follow="-f"
                shift
                ;;
            --analytics|-a)
                use_log_analytics="--analytics"
                shift
                ;;
            mcp-search|caddy)
                container_name="$1"
                shift
                ;;
            *)
                log_warn "Unknown argument: $1"
                shift
                ;;
        esac
    done
    
    cd "$SCRIPT_DIR"
    ACI_NAME=$(terraform output -raw aci_name 2>/dev/null || echo "")
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
    WORKSPACE_ID=$(terraform output -raw log_analytics_workspace_id 2>/dev/null || echo "")
    
    if [ -z "$ACI_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_error "Could not get ACI details from Terraform."
        exit 1
    fi
    
    # Use Log Analytics if available and requested
    if [ -n "$WORKSPACE_ID" ] && [ -n "$use_log_analytics" ]; then
        log_info "Querying logs from Log Analytics workspace..."
        
        local query="ContainerInstanceLog_CL | where ContainerGroup_s == '$ACI_NAME'"
        if [ -n "$container_name" ]; then
            query="$query | where ContainerName_s == '$container_name'"
            log_info "Filtering logs for container: $container_name"
        fi
        query="$query | order by TimeGenerated desc | take 100"
        
        if [ -n "$follow" ]; then
            log_warn "Log Analytics doesn't support --follow. Showing recent logs. Use Azure Portal for live monitoring."
            query="$query | take 50"
        fi
        
        az monitor log-analytics query \
            --workspace "$WORKSPACE_ID" \
            --analytics-query "$query" \
            --output table
    else
        # Use container logs (real-time, but limited retention)
        local cmd="az container logs --name $ACI_NAME --resource-group $RESOURCE_GROUP"
        
        if [ -n "$container_name" ]; then
            cmd="$cmd --container-name $container_name"
            log_info "Viewing logs for container: $container_name"
            if [ -n "$WORKSPACE_ID" ]; then
                log_info "Tip: Use --analytics flag for persistent logs from Log Analytics"
            fi
        else
            log_info "Viewing logs for all containers"
            if [ -n "$WORKSPACE_ID" ]; then
                log_info "Tip: Use --analytics flag for persistent logs from Log Analytics"
            fi
        fi
        
        if [ -n "$follow" ]; then
            cmd="$cmd --follow"
            log_info "Following logs (live updates)..."
        fi
        
        eval "$cmd" || {
            if [ -n "$WORKSPACE_ID" ]; then
                log_warn "Container logs unavailable. Querying Log Analytics instead..."
                view_logs logs "$container_name" "" "--analytics"
            else
                log_error "Failed to retrieve logs. Check container status with: ./deploy.sh status"
                exit 1
            fi
        }
    fi
}

check_container_status() {
    log_info "Checking container instance status..."
    
    cd "$SCRIPT_DIR"
    ACI_NAME=$(terraform output -raw aci_name 2>/dev/null || echo "")
    RESOURCE_GROUP=$(terraform output -raw resource_group_name 2>/dev/null || echo "")
    
    if [ -z "$ACI_NAME" ] || [ -z "$RESOURCE_GROUP" ]; then
        log_error "Could not get ACI details from Terraform."
        exit 1
    fi
    
    log_info "Container Group: $ACI_NAME"
    log_info "Resource Group: $RESOURCE_GROUP"
    echo ""
    
    # Get container group status
    log_info "Container Group Status:"
    az container show \
        --name "$ACI_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "{State:instanceView.state, FQDN:fqdn, IP:ipAddress.ip, Containers:containers[*].{Name:name, Image:image, State:instanceView.currentState.state, RestartCount:instanceView.restartCount}}" \
        --output table
    
    echo ""
    log_info "Container Instances Details:"
    az container show \
        --name "$ACI_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "containers[*].{Name:name, Image:image, CPU:cpu, Memory:memory, Ports:ports[*].{Port:port, Protocol:protocol}}" \
        --output table
    
    echo ""
    log_info "Events (recent):"
    az container show \
        --name "$ACI_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "containers[*].instanceView.events[-5:].{Time:timestamp, Type:type, Message:message}" \
        --output table
}

test_mcp_endpoint() {
    log_info "Testing MCP endpoint..."
    
    cd "$SCRIPT_DIR"
    DOMAIN_NAME=$(terraform output -raw application_url 2>/dev/null | sed 's|https\?://||' || echo "")
    ACI_FQDN=$(terraform output -raw aci_fqdn 2>/dev/null || echo "")
    ACI_IP=$(terraform output -raw aci_ip_address 2>/dev/null || echo "")
    
    if [ -z "$ACI_FQDN" ] && [ -z "$ACI_IP" ]; then
        log_error "Could not get container endpoint details from Terraform."
        exit 1
    fi
    
    # Try domain first if available, otherwise use FQDN, then IP
    if [ -n "$DOMAIN_NAME" ]; then
        ENDPOINT="https://${DOMAIN_NAME}"
        log_info "Testing via domain: $ENDPOINT"
    elif [ -n "$ACI_FQDN" ]; then
        ENDPOINT="http://${ACI_FQDN}"
        log_info "Testing via FQDN: $ENDPOINT"
    else
        ENDPOINT="http://${ACI_IP}"
        log_info "Testing via IP: $ENDPOINT"
    fi
    
    echo ""
    log_info "Testing root endpoint (/)..."
    if curl -s -f -m 10 "$ENDPOINT/" > /dev/null 2>&1; then
        log_info "✓ Root endpoint is responding"
        curl -s -w "\nHTTP Status: %{http_code}\n" "$ENDPOINT/" | head -20
    else
        log_error "✗ Root endpoint failed or timed out"
    fi
    
    echo ""
    log_info "Testing health endpoint (/health)..."
    if curl -s -f -m 10 "$ENDPOINT/health" > /dev/null 2>&1; then
        log_info "✓ Health endpoint is responding"
        curl -s -w "\nHTTP Status: %{http_code}\n" "$ENDPOINT/health"
    else
        log_warn "✗ Health endpoint failed or timed out (container might still be starting)"
        log_info "Response:"
        curl -s -w "\nHTTP Status: %{http_code}\n" "$ENDPOINT/health" || true
    fi
    
    echo ""
    log_info "Testing direct container access (bypassing Caddy)..."
    if [ -n "$ACI_FQDN" ]; then
        DIRECT_ENDPOINT="http://${ACI_FQDN}:8000"
        log_info "Testing: $DIRECT_ENDPOINT/health"
        if curl -s -f -m 10 "$DIRECT_ENDPOINT/health" > /dev/null 2>&1; then
            log_info "✓ Direct container access is working"
            curl -s -w "\nHTTP Status: %{http_code}\n" "$DIRECT_ENDPOINT/health"
        else
            log_warn "✗ Direct container access failed"
            curl -s -w "\nHTTP Status: %{http_code}\n" "$DIRECT_ENDPOINT/health" || true
        fi
    fi
    
    echo ""
    log_info "Summary:"
    log_info "  Application URL: $ENDPOINT"
    log_info "  Health check: $ENDPOINT/health"
    if [ -n "$ACI_FQDN" ]; then
        log_info "  Direct access: http://${ACI_FQDN}:8000/health"
    fi
}

show_outputs() {
    log_info "Deployment outputs:"
    cd "$SCRIPT_DIR"
    terraform output
}

migrate_to_backend() {
    log_info "Migrating Terraform state to Azure Storage backend..."
    
    cd "$SCRIPT_DIR"
    
    # Check if backend is configured
    if ! grep -q 'backend "azurerm"' providers.tf 2>/dev/null || grep -q '^[[:space:]]*#.*backend "azurerm"' providers.tf 2>/dev/null; then
        log_error "Backend is not configured in providers.tf"
        log_info "Please uncomment and configure the backend block first"
        exit 1
    fi
    
    # Check if local state exists
    if [ ! -f "terraform.tfstate" ] && [ ! -f ".terraform/terraform.tfstate" ]; then
        log_warn "No local state file found. Initializing with backend..."
        terraform init
        return
    fi
    
    log_info "Initializing backend and migrating state..."
    terraform init -migrate-state
    
    if [ $? -eq 0 ]; then
        log_info "State migration completed successfully!"
        log_info "Your state is now stored in Azure Storage Account"
        log_info "Local state has been backed up to terraform.tfstate.backup"
    else
        log_error "State migration failed"
        exit 1
    fi
}

create_backend_storage() {
    log_info "Using existing storage account for Terraform backend..."
    
    cd "$SCRIPT_DIR"
    
    # Check if infrastructure is deployed
    if ! terraform output -raw storage_account_name &>/dev/null; then
        log_error "Storage account not found. Please deploy infrastructure first:"
        log_info "  ./deploy.sh deploy"
        exit 1
    fi
    
    # Get storage account details from Terraform output
    STORAGE_ACCOUNT_NAME=$(terraform output -raw storage_account_name)
    RESOURCE_GROUP=$(terraform output -raw resource_group_name)
    CONTAINER_NAME="tfstate"
    
    log_info "Found storage account: $STORAGE_ACCOUNT_NAME"
    log_info "Resource group: $RESOURCE_GROUP"
    
    # Verify container exists (it should be created by Terraform)
    log_info "Verifying container exists..."
    if az storage container show \
        --name "$CONTAINER_NAME" \
        --account-name "$STORAGE_ACCOUNT_NAME" \
        --auth-mode login \
        --output none 2>/dev/null; then
        log_info "Container '$CONTAINER_NAME' already exists"
    else
        log_info "Creating container: $CONTAINER_NAME"
        az storage container create \
            --name "$CONTAINER_NAME" \
            --account-name "$STORAGE_ACCOUNT_NAME" \
            --auth-mode login \
            --output none
        
        if [ $? -ne 0 ]; then
            log_error "Failed to create container"
            exit 1
        fi
    fi
    
    log_info "Storage account ready for Terraform backend!"
    echo ""
    log_info "Next steps:"
    echo "1. Update providers.tf backend block with:"
    echo "   resource_group_name  = \"$RESOURCE_GROUP\""
    echo "   storage_account_name = \"$STORAGE_ACCOUNT_NAME\""
    echo "   container_name       = \"$CONTAINER_NAME\""
    echo ""
    echo "2. Run: ./deploy.sh migrate-backend"
}

# Main script
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  init            - Initialize Terraform"
    echo "  plan            - Plan infrastructure changes"
    echo "  apply           - Apply infrastructure changes"
    echo "  build           - Build and push Docker image to ACR"
    echo "  restart         - Restart the container instance"
    echo "  deploy          - Full deployment (init, plan, apply, build, restart)"
    echo "  status          - Check container instance status and health"
    echo "  test            - Test MCP endpoint with curl (health check)"
    echo "  logs [container] [-f] [--analytics] - View container logs"
    echo "                        container: mcp-search, caddy, or omit for all"
    echo "                        -f: follow logs (live updates, container logs only)"
    echo "                        --analytics: query Log Analytics (persistent logs)"
    echo "  outputs         - Show Terraform outputs"
    echo "  create-backend  - Show storage account details for Terraform backend"
    echo "  migrate-backend - Migrate local state to Azure Storage backend"
    echo "  destroy         - Destroy all infrastructure"
    echo ""
    echo "Log Examples:"
    echo "  ./deploy.sh logs                    # View all container logs (real-time)"
    echo "  ./deploy.sh logs mcp-search          # View MCP Search logs"
    echo "  ./deploy.sh logs caddy               # View Caddy logs"
    echo "  ./deploy.sh logs mcp-search -f       # Follow MCP Search logs (live)"
    echo "  ./deploy.sh logs mcp-search --analytics # Query Log Analytics (persistent)"
    echo ""
}

case "${1:-}" in
    init)
        check_prerequisites
        init_terraform
        ;;
    plan)
        check_prerequisites
        plan_infrastructure
        ;;
    apply)
        check_prerequisites
        apply_infrastructure
        ;;
    build)
        check_prerequisites
        build_and_push_image
        ;;
    restart)
        check_prerequisites
        restart_container
        ;;
    deploy)
        check_prerequisites
        init_terraform
        plan_infrastructure
        apply_infrastructure
        build_and_push_image
        restart_container
        show_outputs
        ;;
    status)
        check_prerequisites
        check_container_status
        ;;
    test)
        check_prerequisites
        test_mcp_endpoint
        ;;
    logs)
        check_prerequisites
        view_logs "$@"
        ;;
    outputs)
        show_outputs
        ;;
    create-backend)
        check_prerequisites
        create_backend_storage
        ;;
    migrate-backend)
        check_prerequisites
        migrate_to_backend
        ;;
    destroy)
        check_prerequisites
        log_warn "This will destroy all infrastructure!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            cd "$SCRIPT_DIR"
            terraform destroy
        else
            log_info "Destroy cancelled."
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac
