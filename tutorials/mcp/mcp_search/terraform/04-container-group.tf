# ============================================================================
# Container Group
# Depends on: foundation.tf, container-registry.tf, key-vault.tf, identity.tf, 
#             container-mcp-search.tf, container-caddy.tf
# 
# This file defines the Azure Container Group that hosts all containers.
# Container configurations are defined in their respective files.
# ============================================================================

# ----------------------------------------------------------------------------
# ACR Password Secret (for audit/backup)
# ----------------------------------------------------------------------------

resource "azurerm_key_vault_secret" "acr_password" {
  name         = "acr-password"
  value        = azurerm_container_registry.main.admin_password
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_container_group" "main" {
  name                = "aci-${local.base_name}-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location
  os_type             = "Linux"
  ip_address_type     = "Public"
  dns_name_label      = "aci-${local.base_name}-${local.suffix}"

  # Use managed identity if enabled, otherwise rely on admin credentials
  dynamic "identity" {
    for_each = var.use_managed_identity_for_acr ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.aci.id]
    }
  }

  # Always use admin credentials for ACR access (works without role assignments)
  image_registry_credential {
    server   = azurerm_container_registry.main.login_server
    username = azurerm_container_registry.main.admin_username
    password = azurerm_container_registry.main.admin_password
  }

  # -------------------------------------------------------------------------
  # MCP Search Application Container
  # Configuration defined in: 04-container-mcp-search.tf
  # -------------------------------------------------------------------------
  container {
    name   = local.mcp_search_container.name
    image  = local.mcp_search_container.image
    cpu    = local.mcp_search_container.cpu
    memory = local.mcp_search_container.memory

    dynamic "ports" {
      for_each = local.mcp_search_container.ports
      content {
        port     = ports.value.port
        protocol = ports.value.protocol
      }
    }

    environment_variables = local.mcp_search_container.environment_variables

    secure_environment_variables = local.mcp_search_container.secure_environment_variables
  }

  # -------------------------------------------------------------------------
  # Caddy Reverse Proxy Container
  # Configuration defined in: 04-container-caddy.tf
  # -------------------------------------------------------------------------
  container {
    name   = local.caddy_container.name
    image  = local.caddy_container.image
    cpu    = local.caddy_container.cpu
    memory = local.caddy_container.memory

    dynamic "ports" {
      for_each = local.caddy_container.ports
      content {
        port     = ports.value.port
        protocol = ports.value.protocol
      }
    }

    environment_variables = local.caddy_container.environment_variables

    commands = local.caddy_container.commands

    dynamic "volume" {
      for_each = local.caddy_container.volumes
      content {
        name                 = volume.value.name
        mount_path           = volume.value.mount_path
        storage_account_name = volume.value.storage_account_name
        storage_account_key  = volume.value.storage_account_key
        share_name           = volume.value.share_name
      }
    }
  }

  exposed_port {
    port     = 80
    protocol = "TCP"
  }

  exposed_port {
    port     = 443
    protocol = "TCP"
  }

  tags = var.tags

  depends_on = [
    azurerm_key_vault_access_policy.aci,
  ]
}
