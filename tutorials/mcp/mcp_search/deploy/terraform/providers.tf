# ============================================================================
# Terraform Configuration
# ============================================================================

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
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }

  # Uncomment and configure for remote state storage
  # See BACKEND_SETUP.md for detailed instructions
  #
  # The storage account is created by this Terraform configuration, so you can:
  # 1. Deploy first with local state (default)
  # 2. After deployment, get the storage account name: terraform output storage_account_name
  # 3. Uncomment the backend block below and use the output value
  # 4. Run: terraform init (will prompt to migrate state)
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-mcp-search"              # Your resource group name
  #   storage_account_name = "stsearchmcp<xxxxxx>"        # Get from: terraform output storage_account_name
  #   container_name       = "tfstate"                    # Container created automatically
  #   key                  = "mcp-search.tfstate"        # State file name
  #   # Optional: use managed identity instead of access key
  #   # use_azuread_auth     = true
  # }
}

# ============================================================================
# Provider Configuration
# ============================================================================

provider "azurerm" {
  subscription_id = var.subscription_id # Optional - uses default from Azure CLI if not set

  # Automatically register required Azure resource providers
  resource_provider_registrations = "extended"

  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "random" {}
provider "null" {}
