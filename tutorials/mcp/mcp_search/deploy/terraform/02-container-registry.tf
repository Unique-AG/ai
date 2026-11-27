# ============================================================================
# Azure Container Registry
# Depends on: foundation.tf (locals, data sources)
# ============================================================================

resource "azurerm_container_registry" "main" {
  name                = "acr${var.base_name_clean}${local.suffix}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = var.tags
}
