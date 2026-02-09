# MCP Search - Azure Terraform Deployment

This Terraform configuration deploys the MCP Search application to Azure with the following resources:

## Architecture

```mermaid
flowchart TB
    subgraph Internet
        User[User]
    end

    subgraph Azure["Azure Resource Group"]
        subgraph ACI["Azure Container Instance"]
            Caddy["Caddy\n:80/:443"]
            App["MCP Search\n:8003"]
        end

        ACR["Azure Container Registry\n(Docker Images)"]
        KV["Azure Key Vault\n(Secrets)"]
        Storage["Storage Account\n(Certs + TF State)"]
        Identity["Managed Identity"]
    end

    User -->|HTTPS| Caddy
    Caddy -->|Proxy| App
    Caddy -->|Persist certs| Storage
    ACR -->|Pull image| ACI
    KV -->|Inject secrets| ACI
    Identity -->|Access| ACR
    Identity -->|Access| KV
```

## Resources Created

| Resource | Name Pattern | Purpose |
|----------|-------------|---------|
| Container Registry | `acrsearchmcp<suffix>` | Stores Docker images |
| Key Vault | `kv-search-mcp-<suffix>` | Stores application secrets |
| Storage Account | `stsearchmcp<suffix>` | Stores Caddy certificates + Terraform state |
| Log Analytics Workspace | `law-search-mcp-<suffix>` | Centralized logging (30 days retention) |
| Container Instance | `aci-search-mcp-<suffix>` | Runs the application containers |
| Managed Identity | `id-search-mcp-<suffix>` | Provides secure access to resources |

## Prerequisites

1. **Azure CLI** - [Install](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. **Terraform** >= 1.5.0 - [Install](https://www.terraform.io/downloads)
3. **Docker** - [Install](https://docs.docker.com/get-docker/)
4. **Azure Subscription** with appropriate permissions

## Quick Start

### 1. Login to Azure

```bash
# Login to Azure
az login

# Set the default subscription (required for Terraform)
az account set --subscription "Your Subscription Name"

# Verify the subscription is set
az account show
```

**Note**: If you get a "subscription ID could not be determined" error, either:
- Set the subscription via Azure CLI (as shown above), or
- Set it in `terraform.tfvars`: `subscription_id = "your-subscription-id"`
- Or set environment variable: `export ARM_SUBSCRIPTION_ID="your-subscription-id"`

### 2. Create Resource Group (if it doesn't exist)

```bash
az group create --name rg-mcp-search --location westeurope
```

### 3. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 4. Deploy

Using the deployment script:

```bash
chmod +x deploy.sh
./deploy.sh deploy
```

Or manually:

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the configuration
terraform apply tfplan

# Build and push Docker image (automatically tagged with git SHA + timestamp)
az acr login --name $(terraform output -raw acr_name)
cd ..
az acr build --registry $(terraform output -raw acr_name) \
  --image mcp-search:$(git rev-parse --short HEAD)-$(date +%Y%m%d-%H%M%S) \
  --image mcp-search:latest .
```

### 5. Verify Deployment

After deployment, verify that everything is working correctly:

```bash
# Comprehensive verification (recommended)
./deploy.sh verify

# Or run the verification script directly
./verify-deployment.sh
```

The verification script checks:
- ✅ Terraform state and outputs
- ✅ Azure resources exist (Resource Group, ACR, Key Vault, Storage, Container Instance)
- ✅ Container instances are running
- ✅ Health endpoints are accessible
- ✅ Key Vault secrets are present
- ✅ Container Registry accessibility
- ✅ Log Analytics connectivity

### 6. Configure DNS

After deployment, create a DNS record pointing your domain to the container IP:

```bash
# Get the IP address
terraform output aci_ip_address

# Create an A record:
# your-domain.com -> <IP_ADDRESS>
```

## Variables

### Required Variables

| Variable | Description |
|----------|-------------|
| `resource_group_name` | Name of the Azure Resource Group |
| `location` | Azure region (e.g., `westeurope`) |
| `base_name` | Base name for resources with hyphens (e.g., `search-mcp` → `kv-search-mcp-xxx`) |
| `base_name_clean` | Base name without hyphens for Storage/ACR (e.g., `searchmcp` → `stsearchmcpxxx`) |
| `domain_name` | Domain name for HTTPS (must be a domain you own with DNS pointing to ACI, or use the ACI FQDN for HTTP-only) |
| `caddy_email` | Email for Let's Encrypt notifications |
| `unique_app_key` | UNIQUE_APP_KEY environment variable |
| `unique_app_id` | UNIQUE_APP_ID environment variable |
| `unique_api_base_url` | UNIQUE_API_BASE_URL environment variable |
| `unique_auth_company_id` | UNIQUE_AUTH_COMPANY_ID environment variable |
| `unique_auth_user_id` | UNIQUE_AUTH_USER_ID environment variable |
| `unique_app_endpoint` | UNIQUE_APP_ENDPOINT environment variable |
| `unique_app_endpoint_secret` | UNIQUE_APP_ENDPOINT_SECRET environment variable |
| `zitadel_base_url` | ZITADEL_BASE_URL environment variable |
| `zitadel_client_id` | ZITADEL_CLIENT_ID environment variable |
| `zitadel_client_secret` | ZITADEL_CLIENT_SECRET environment variable |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `app_container_cpu` | `1` | CPU cores for app container |
| `app_container_memory` | `1.5` | Memory (GB) for app container |
| `caddy_container_cpu` | `0.5` | CPU cores for Caddy container |
| `caddy_container_memory` | `0.5` | Memory (GB) for Caddy container |
| `app_image_tag` | `latest` | Docker image tag |
| `use_managed_identity_for_acr` | `true` | Use managed identity for ACR (set to `false` if you lack role assignment permissions) |
| `tags` | See defaults | Resource tags |

## Secrets Management

**⚠️ IMPORTANT: Never commit secrets to version control!**

The `.gitignore` file is configured to exclude `terraform.tfvars` and other sensitive files. Always use `terraform.tfvars.example` as a template.

### Option 1: Environment Variables (Recommended for CI/CD)

Set environment variables with the `TF_VAR_` prefix:

```bash
export TF_VAR_resource_group_name="rg-mcp-search"
export TF_VAR_location="westeurope"
export TF_VAR_base_name="search-mcp"
export TF_VAR_base_name_clean="searchmcp"
export TF_VAR_domain_name="mcp-search.yourdomain.com"
export TF_VAR_caddy_email="admin@yourdomain.com"
# ... add all other variables
```

Then run Terraform normally:
```bash
terraform plan
terraform apply
```

### Option 2: terraform.tfvars (Local Development Only)

1. Copy the example file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your actual values (this file is gitignored)

3. Run Terraform:
   ```bash
   terraform plan
   terraform apply
   ```

## Deployment Script Commands

```bash
./deploy.sh init            # Initialize Terraform
./deploy.sh plan            # Plan infrastructure changes
./deploy.sh apply           # Apply infrastructure changes
./deploy.sh build           # Build and push Docker image to ACR
./deploy.sh restart         # Restart the container instance
./deploy.sh deploy          # Full deployment (all of the above)
./deploy.sh status          # Check container instance status and health
./deploy.sh test            # Test MCP endpoint with curl (health check)
./deploy.sh logs [container] [-f]  # View container logs
./deploy.sh outputs         # Show Terraform outputs
./deploy.sh create-backend  # Show storage account details for Terraform backend
./deploy.sh migrate-backend # Migrate local state to Azure Storage backend
./deploy.sh destroy         # Destroy all infrastructure
```

### Checking Container Status

```bash
# Check container status, health, and recent events
./deploy.sh status
```

### Testing the MCP Endpoint

```bash
# Automated test (recommended)
./deploy.sh test
```

**Quick manual tests:**
```bash
# Get endpoint URLs
terraform output application_url
terraform output aci_fqdn

# Test health endpoint
curl http://$(terraform output -raw aci_fqdn)/health

# Test direct container access
curl http://$(terraform output -raw aci_fqdn):8003/health

# Test MCP protocol endpoint
curl -X POST http://$(terraform output -raw aci_fqdn):8003/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### Viewing Container Logs

**Real-time Container Logs:**
```bash
# View all container logs
./deploy.sh logs

# View logs from a specific container
./deploy.sh logs mcp-search   # MCP Search application logs
./deploy.sh logs caddy        # Caddy reverse proxy logs

# Follow logs in real-time (live updates)
./deploy.sh logs mcp-search -f
./deploy.sh logs caddy -f
```

**Log Analytics (Persistent Storage, 30 days retention):**
```bash
# Query logs from Log Analytics workspace
./deploy.sh logs mcp-search --analytics
./deploy.sh logs caddy --analytics

# Or use Azure CLI directly
az monitor log-analytics query \
  --workspace $(terraform output -raw log_analytics_workspace_id) \
  --analytics-query "ContainerInstanceLog_CL | where ContainerGroup_s == '$(terraform output -raw aci_name)' | order by TimeGenerated desc | take 100"
```

**Access Log Analytics in Azure Portal:**
```bash
# Get the portal URL
terraform output log_analytics_portal_url
```

## HTTPS Setup

The Caddy configuration **automatically detects** whether to use:
- **Self-signed certificates** for Azure FQDNs (`*.azurecontainer.io`)
- **Let's Encrypt certificates** for custom domains

### For Azure FQDNs (No Domain Needed)

When you use the Azure Container Instance FQDN (e.g., `aci-search-mcp-xxx.swedencentral.azurecontainer.io`):

1. ✅ **HTTPS is enabled** with self-signed certificates
2. ✅ **Port 443 is available** for HTTPS connections
3. ⚠️ **Browsers will show security warnings** (expected for self-signed certs)
4. ✅ **MCP clients can connect** (may need to disable certificate validation)

### For Custom Domains

When you use a custom domain you own:

1. ✅ **Let's Encrypt automatically provisions** certificates
2. ✅ **Fully trusted** by browsers and clients
3. ✅ **No security warnings**
4. ⚠️ **Requires DNS configuration** pointing to the ACI IP

### Testing HTTPS

**With curl (ignore certificate validation):**
```bash
# Test HTTPS endpoint (ignore self-signed cert warning)
curl -k https://$(terraform output -raw aci_fqdn)/health

# Test MCP endpoint
curl -k -X POST https://$(terraform output -raw aci_fqdn)/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

**With Python (disable SSL verification):**
```python
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test endpoint
response = requests.get(
    f'https://{aci_fqdn}/health',
    verify=False  # Disable certificate verification
)
print(response.json())
```

### Getting a Real Certificate

If you want a **trusted Let's Encrypt certificate**:

1. **Use a domain you own**:
   - Create a subdomain (e.g., `mcp-search.yourdomain.com`)
   - Point DNS to your ACI IP: `terraform output aci_ip_address`
   - Update `terraform.tfvars`: `domain_name = "mcp-search.yourdomain.com"`
   - Apply changes: `terraform apply && ./deploy.sh restart`

2. **Use a free domain service**:
   - **DuckDNS** (Recommended): https://www.duckdns.org/
   - Create a free subdomain (e.g., `myapp.duckdns.org`)
   - Update DNS to point to your ACI IP
   - Update `domain_name` in `terraform.tfvars`

Caddy will automatically:
- Request Let's Encrypt certificate
- Validate domain ownership
- Provision trusted certificate
- Enable HTTPS

## Remote State Backend (Optional but Recommended)

For team collaboration, use Azure Storage Account as a Terraform backend to store state remotely.

### Quick Setup (After First Deployment)

**Option 1: Using the deployment script** (easiest):
```bash
# After your first successful deployment with local state:
./deploy.sh create-backend    # Shows storage account details (already created!)
# Edit providers.tf with the storage account name from output
./deploy.sh migrate-backend  # Migrates state to remote backend
```

**Option 2: Manual setup:**
1. Deploy infrastructure first: `./deploy.sh deploy` (creates storage account automatically)
2. Get storage account name: `terraform output storage_account_name`
3. Uncomment backend config in `providers.tf` and use the storage account name
4. Run `terraform init` and answer "yes" when prompted to migrate state

**Note**: The storage account is shared between Caddy certificates and Terraform backend - no need for a separate storage account!

### Backend Configuration

Uncomment and update the backend configuration in `providers.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-mcp-search"           # Your resource group
    storage_account_name = "stsearchmcp<xxxxxx>"     # From terraform output
    container_name       = "tfstate"                  # Container created automatically
    key                  = "mcp-search.tfstate"       # State file name
  }
}
```

Then run:
```bash
terraform init  # Will prompt to migrate existing state - answer "yes"
```

## Updating the Application

After making code changes:

```bash
# Build and push new image (tagged with git SHA + timestamp for traceability)
./deploy.sh build

# Restart container to pull new image
./deploy.sh restart
```

The build command automatically:
- Tags images with `{git-sha}-{timestamp}` format (e.g., `a1b2c3d-20260205-143052`)
- Also tags as `latest` for container compatibility
- Logs the full git SHA for deployment traceability

### Docker Build Issues

If you encounter network timeouts or Docker Hub rate limiting:

**Option 1: Retry** (often resolves transient network issues)
```bash
./deploy.sh build
```

**Option 2: Build locally and push**
```bash
# Login to ACR
az acr login --name $(terraform output -raw acr_name)

# Generate version tag
IMAGE_TAG="$(git rev-parse --short HEAD)-$(date +%Y%m%d-%H%M%S)"
ACR_SERVER=$(terraform output -raw acr_login_server)

# Build locally with versioned tag
docker build -t ${ACR_SERVER}/mcp-search:${IMAGE_TAG} ..
docker tag ${ACR_SERVER}/mcp-search:${IMAGE_TAG} ${ACR_SERVER}/mcp-search:latest

# Push both tags to ACR
docker push ${ACR_SERVER}/mcp-search:${IMAGE_TAG}
docker push ${ACR_SERVER}/mcp-search:latest

# Restart container
./deploy.sh restart
```

## Troubleshooting

### No Logs or Containers Not Running

```bash
# 1. Check container status first
./deploy.sh status

# 2. If containers are stopped, restart them
./deploy.sh restart

# 3. View logs after restart
./deploy.sh logs mcp-search -f

# 4. Check container events for errors
az container show \
  --name $(terraform output -raw aci_name) \
  --resource-group $(terraform output -raw resource_group_name) \
  --query "containers[*].instanceView.events" \
  --output table
```

**Common Issues:**

1. **Container Image Not Found**: Make sure you've built and pushed the image:
   ```bash
   ./deploy.sh build
   ```

2. **Container Crashed**: Check events for crash reasons:
   ```bash
   ./deploy.sh status
   ```

3. **No Logs Yet**: Containers might be starting up. Wait a few seconds and try again, or use `-f` to follow:
   ```bash
   ./deploy.sh logs mcp-search -f
   ```

4. **Container Group Stopped**: Restart the container group:
   ```bash
   ./deploy.sh restart
   ```

### Subscription ID Error

If you see: `Error: subscription ID could not be determined and was not specified`

**Solution 1** (Recommended): Set default subscription via Azure CLI
```bash
az account set --subscription "Your Subscription Name or ID"
az account show  # Verify it's set
```

**Solution 2**: Set subscription ID in `terraform.tfvars`
```hcl
subscription_id = "12345678-1234-1234-1234-123456789012"
```

**Solution 3**: Set environment variable
```bash
export ARM_SUBSCRIPTION_ID="12345678-1234-1234-1234-123456789012"
```

### Resource Provider Registration Error

If you see: `Error: Terraform does not have the necessary permissions to register Resource Providers`

**Required Resource Providers** (must be registered by a subscription admin):

```bash
# Register the required providers (requires Contributor or Owner role)
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.ContainerInstance
az provider register --namespace Microsoft.OperationalInsights

# Check registration status
az provider show --namespace Microsoft.ContainerRegistry --query "registrationState"
```

**Note**: If you don't have permissions to register providers, ask your Azure subscription administrator to register them. Registration typically takes 1-2 minutes per provider.

### Role Assignment Permission Error

If you see: `Error: does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write'`

This happens when Terraform tries to assign the `AcrPull` role to the managed identity but you don't have User Access Administrator or Owner permissions.

**Solution 1** (Quickest): Disable managed identity for ACR

Add to your `terraform.tfvars`:
```hcl
use_managed_identity_for_acr = false
```

**Solution 2**: Ask an admin to grant the role

Have a subscription Owner or User Access Administrator run:
```bash
az role assignment create \
  --assignee "your-email@domain.com" \
  --role "User Access Administrator" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group-name>"
```

**Note**: If you have Owner permissions on the resource group, you already have the ability to create role assignments. The managed identity is still created and used for Key Vault access via RBAC, so that works regardless of this setting.

### Certificate Errors in Browser

**Expected for self-signed certificates.** To proceed:
1. Click "Advanced" or "Show Details"
2. Click "Proceed to site" or "Accept the risk"
3. The connection is still encrypted, just not verified by a CA

### MCP Client Rejects Certificate

Configure your MCP client to:
- Disable SSL verification (for testing)
- Or add the self-signed certificate to trusted store
- Or use a custom domain with Let's Encrypt certificate

### Let's Encrypt Fails

If using a custom domain and Let's Encrypt fails:
1. Check DNS is configured correctly
2. Verify domain resolves to ACI IP
3. Check Caddy logs: `./deploy.sh logs caddy`
4. Ensure port 80 is accessible (required for HTTP-01 challenge)

## Costs

Approximate monthly costs (West Europe, as of 2024):

| Resource | SKU | Estimated Cost |
|----------|-----|---------------|
| Container Registry | Basic | ~$5/month |
| Key Vault | Standard | ~$0.03/10k operations |
| Storage Account | Standard LRS | ~$0.02/GB |
| Container Instance | 1.5 CPU, 2GB RAM | ~$50-70/month |

**Total: ~$60-80/month**

## Security Considerations

1. **Secrets**: All sensitive values are stored in Azure Key Vault (for audit/backup) and passed securely to containers
2. **Container Registry**: Managed identity is used by default; set `use_managed_identity_for_acr = false` if you lack permissions
3. **HTTPS**: Caddy automatically provisions and renews Let's Encrypt certificates
4. **Network**: Consider adding NSG rules or using Azure Firewall for additional security
5. **Identity**: User-assigned managed identity is used for Key Vault access
6. **State**: Use remote backend (Azure Storage) for team collaboration

## Clean Up

To destroy all resources:

```bash
./deploy.sh destroy
# Or manually:
terraform destroy
```

**Warning**: This will delete all resources including the Key Vault and its secrets. Make sure to backup any important data first.
