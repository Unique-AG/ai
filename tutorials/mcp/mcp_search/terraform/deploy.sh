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
    log_info "Building image using ACR Tasks..."
    cd "$PROJECT_DIR"
    az acr build --registry "$ACR_NAME" --image mcp-search:latest .
    
    log_info "Image pushed successfully to $ACR_LOGIN_SERVER/mcp-search:latest"
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
    echo "  outputs         - Show Terraform outputs"
    echo "  create-backend  - Show storage account details for Terraform backend"
    echo "  migrate-backend - Migrate local state to Azure Storage backend"
    echo "  destroy         - Destroy all infrastructure"
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
