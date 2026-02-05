# ============================================================================
# Foundation Resources
# No dependencies - these are the base resources used by all other modules
# ============================================================================

# Data Sources
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

data "azurerm_client_config" "current" {}

# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Local values for naming conventions
locals {
  # Base name for resources (Azure naming has different constraints)
  base_name       = "search-mcp"
  base_name_clean = "searchmcp" # For resources that don't allow hyphens
  suffix          = random_string.suffix.result
}
