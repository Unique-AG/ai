# ============================================================================
# Log Analytics Workspace (Infrastructure)
# Depends on: foundation.tf (data sources, locals)
# 
# This provides centralized logging for container instances.
# Container logs are automatically sent to Log Analytics for persistent storage
# and advanced querying capabilities.
# ============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.base_name}-${local.suffix}"
  location            = var.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}
