# Terraform Backend Setup with Azure Storage

## What Your Colleague Means

Your colleague Dominik is suggesting using **Azure Storage Account** as a **Terraform backend** to store the Terraform state file remotely instead of locally.

### The Problem with Local State

Currently, Terraform stores state in a local file (`terraform.tfstate`). This causes issues:

- ❌ **State conflicts**: Multiple people can't work on the same infrastructure
- ❌ **Lost state**: If you delete the file, Terraform loses track of resources
- ❌ **No locking**: Two people can run `terraform apply` simultaneously
- ❌ **Not backed up**: Local files can be lost

### The Solution: Remote Backend

Using Azure Storage Account as a backend:
- ✅ **Shared state**: Multiple team members can use the same state
- ✅ **State locking**: Prevents concurrent modifications
- ✅ **Backed up**: Stored in Azure (durable and redundant)
- ✅ **Version history**: Can enable versioning on the storage account

### The "Chicken and Egg" Problem

Your colleague mentions: *"you can't terraform the backend without a backend"*

This means:
- You need a backend to store Terraform state
- But you can't create that backend using Terraform (because you need a backend first!)
- **Solution**: Create the storage account manually first ("clickops" = clicking in Azure Portal)

## Two Approaches

### Approach 1: Start Local, Migrate Later (Recommended for First Deployment)

**Best for**: When you want to deploy first, then migrate to remote state

1. Deploy with local state (default - no backend configured)
2. After successful deployment, create storage account
3. Migrate state to remote backend
4. Future operations use remote state automatically

See [Migration Workflow](#migration-workflow-after-first-deployment) below.

### Approach 2: Setup Backend First

**Best for**: When you know you'll need shared state from the start

1. Create storage account first
2. Configure backend before first deployment
3. Deploy directly to remote state

## Step-by-Step Setup

### Step 1: Storage Account Already Created! 🎉

**Good news**: The storage account is created automatically by Terraform! It's shared between:
- Caddy certificates (file shares)
- Terraform backend state (blob container)

**No manual creation needed** - just deploy the infrastructure first, then configure the backend.

### Step 2: Get Storage Account Details

After deploying infrastructure, get the storage account name:

```bash
cd terraform
terraform output storage_account_name
terraform output resource_group_name
```

Or use the helper script:
```bash
./deploy.sh create-backend  # Shows you the values to use
```

### Step 3: Configure Terraform Backend

Uncomment and update the backend configuration in `providers.tf`:

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-mcp-search"           # Your resource group (from terraform output)
    storage_account_name = "stsearchmcp<xxxxxx>"      # Storage account name (from terraform output storage_account_name)
    container_name       = "tfstate"                  # Container name (created automatically)
    key                  = "mcp-search.tfstate"       # State file name
  }
}
```

### Step 4: Migrate Existing State (If Any)

If you already have a local state file:

```bash
cd terraform

# Initialize with backend (will prompt to migrate)
terraform init

# When prompted: "Do you want to copy existing state to the new backend?"
# Answer: yes
```

## Migration Workflow (After First Deployment)

This is the workflow you asked about - deploy locally first, then migrate to remote state.

### Step 1: Deploy with Local State

Start with no backend configured (default):

```bash
cd terraform
terraform init  # Uses local backend
terraform plan
terraform apply  # State stored locally in terraform.tfstate
```

### Step 2: Get Storage Account Details

The storage account is already created! Get its name:

```bash
cd terraform
terraform output storage_account_name
terraform output resource_group_name
```

Or use the helper:
```bash
./deploy.sh create-backend  # Shows you what to configure
```

### Step 3: Configure Backend

Now uncomment and configure the backend in `providers.tf` using the values from Step 2:

```hcl
backend "azurerm" {
  resource_group_name  = "rg-mcp-search"              # From terraform output
  storage_account_name = "stsearchmcp<xxxxxx>"         # From terraform output storage_account_name
  container_name       = "tfstate"                     # Container created automatically
  key                  = "mcp-search.tfstate"
}
```

**Note**: The storage account is shared with Caddy certificates - no need for a separate storage account!

### Step 4: Migrate State

Run `terraform init` - it will detect the backend change and offer to migrate:

```bash
terraform init

# Output will show:
# Initializing the backend...
# Do you want to copy existing state to the new backend?
#   Enter "yes" to copy and "no" to start with an empty state.
# 
# Enter a value: yes
```

**Important**: Type `yes` to migrate your existing state!

### Step 5: Verify Migration

```bash
# Verify state is now remote
terraform state list  # Should show all your resources

# Verify local state file is backed up
ls -la terraform.tfstate.backup  # Backup of old local state

# The new state is in Azure Storage, not local
# terraform.tfstate should be empty or minimal
```

### Step 6: Future Operations

From now on, all Terraform operations use the remote backend:

```bash
terraform plan   # Reads from Azure Storage
terraform apply  # Writes to Azure Storage
terraform destroy  # Uses remote state
```

**Benefits:**
- ✅ State is now shared with your team
- ✅ Automatic locking prevents conflicts
- ✅ Backed up in Azure
- ✅ No need to commit state files to git

### Step 5: Verify It Works

```bash
# Check that state is now remote
terraform state list

# The state file should no longer exist locally
ls -la terraform.tfstate  # Should not exist
```

## Security Best Practices

### Option 1: Use Storage Account Key (Simpler)

Store the key as an environment variable:

```bash
export ARM_ACCESS_KEY="<storage-account-key-from-step-2>"
```

Then remove it from the backend config (Terraform will use the env var).

### Option 2: Use Managed Identity (More Secure)

If running from Azure (e.g., GitHub Actions, Azure DevOps):

```hcl
backend "azurerm" {
  resource_group_name  = "rg-mcp-search"
  storage_account_name = "stterraformstatexxxx"
  container_name       = "tfstate"
  key                  = "mcp-search.tfstate"
  use_azuread_auth     = true  # Use managed identity instead of key
}
```

## Multiple Environments

You can use different state files for different environments:

```hcl
# For production
key = "mcp-search-prod.tfstate"

# For staging
key = "mcp-search-staging.tfstate"

# For development
key = "mcp-search-dev.tfstate"
```

Or use different containers:
```hcl
container_name = "tfstate-prod"
container_name = "tfstate-staging"
container_name = "tfstate-dev"
```

## State Locking

Azure Storage backend automatically provides state locking:
- When you run `terraform apply`, it creates a lock file
- Other users will see: "Error: Error acquiring the state lock"
- Lock is released when `terraform apply` completes (or fails)
- Manual unlock: `terraform force-unlock <lock-id>`

## Troubleshooting

### "Backend configuration changed"
If you change backend config, run:
```bash
terraform init -migrate-state
```

### "Storage account not found"
- Verify the storage account name is correct
- Check you're in the right subscription: `az account show`

### "Access denied"
- Verify the storage account key is correct
- Or ensure managed identity has "Storage Blob Data Contributor" role

## Summary

Your colleague's suggestion is a **best practice** for team collaboration:

1. ✅ **Manually create** storage account first (clickops)
2. ✅ **Configure backend** in `providers.tf`
3. ✅ **Migrate state** with `terraform init`
4. ✅ **Enjoy** shared state, locking, and backups!

This is especially important if multiple people will be managing the infrastructure!
