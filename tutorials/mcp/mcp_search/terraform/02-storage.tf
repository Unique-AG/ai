# ============================================================================
# Storage Account (Infrastructure)
# Depends on: foundation.tf (data sources, locals)
# 
# This provides the storage account infrastructure. Containers define their own
# file shares and blob containers as needed.
# ============================================================================

resource "azurerm_storage_account" "main" {
  name                     = "st${var.base_name_clean}${local.suffix}"
  resource_group_name      = data.azurerm_resource_group.main.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Enable blob versioning for Terraform state (optional but recommended)
  blob_properties {
    versioning_enabled = true
  }

  # Ignore changes to static website properties to avoid 404 errors
  # when Terraform tries to read non-existent static website configuration
  lifecycle {
    ignore_changes = [
      # Ignore static website properties that may not exist
      # This prevents 404 errors when Terraform tries to read them
    ]
  }

  tags = var.tags
}

# Blob container for Terraform state (created for backend migration)
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}
