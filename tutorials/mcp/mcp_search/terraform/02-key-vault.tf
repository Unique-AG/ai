# ============================================================================
# Azure Key Vault (Infrastructure)
# Depends on: foundation.tf (data sources, locals)
# 
# This provides the Key Vault infrastructure. Containers define their own
# secrets as needed.
# ============================================================================

resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.base_name}-${local.suffix}"
  resource_group_name        = data.azurerm_resource_group.main.name
  location                   = var.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  # Access policy for Terraform deployment
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Purge",
      "Recover",
    ]
  }

  tags = var.tags
}
