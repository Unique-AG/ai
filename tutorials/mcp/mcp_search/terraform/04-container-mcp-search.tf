# ============================================================================
# MCP Search Container
# Depends on: foundation.tf, container-registry.tf, key-vault.tf, identity.tf
# 
# This file defines everything the MCP Search container needs:
# - Key Vault secrets it uses
# - Container configuration
# ============================================================================

# ----------------------------------------------------------------------------
# Key Vault Secrets (defined by this container)
# Note: Secrets are stored in Key Vault for audit/backup purposes.
# The container receives secrets directly via secure_environment_variables.
# ----------------------------------------------------------------------------

resource "azurerm_key_vault_secret" "unique_app_key" {
  name         = "unique-app-key"
  value        = var.unique_app_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_app_id" {
  name         = "unique-app-id"
  value        = var.unique_app_id
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_api_base_url" {
  name         = "unique-api-base-url"
  value        = var.unique_api_base_url
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_auth_company_id" {
  name         = "unique-auth-company-id"
  value        = var.unique_auth_company_id
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_auth_user_id" {
  name         = "unique-auth-user-id"
  value        = var.unique_auth_user_id
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_app_endpoint" {
  name         = "unique-app-endpoint"
  value        = var.unique_app_endpoint
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "unique_app_endpoint_secret" {
  name         = "unique-app-endpoint-secret"
  value        = var.unique_app_endpoint_secret
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "zitadel_base_url" {
  name         = "zitadel-base-url"
  value        = var.zitadel_base_url
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "zitadel_client_id" {
  name         = "zitadel-client-id"
  value        = var.zitadel_client_id
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "zitadel_client_secret" {
  name         = "zitadel-client-secret"
  value        = var.zitadel_client_secret
  key_vault_id = azurerm_key_vault.main.id
}

# ----------------------------------------------------------------------------
# Container Configuration (as local for reference in container group)
# ----------------------------------------------------------------------------

locals {
  mcp_search_container = {
    name   = "mcp-search"
    image  = "${azurerm_container_registry.main.login_server}/mcp-search:${var.app_image_tag}"
    cpu    = var.app_container_cpu
    memory = var.app_container_memory

    ports = [
      {
        port     = 8000
        protocol = "TCP"
      }
    ]

    environment_variables = {
      # Server settings
      "MCP_SERVER_BASE_URL"       = "https://${var.domain_name}"
      "MCP_SERVER_LOCAL_BASE_URL" = "http://localhost:8000"
      "MCP_SERVER_TRANSPORT"      = "streamable-http"
    }

    secure_environment_variables = {
      # Unique settings
      "UNIQUE_APP_KEY"             = var.unique_app_key
      "UNIQUE_APP_ID"              = var.unique_app_id
      "UNIQUE_API_BASE_URL"        = var.unique_api_base_url
      "UNIQUE_AUTH_COMPANY_ID"     = var.unique_auth_company_id
      "UNIQUE_AUTH_USER_ID"        = var.unique_auth_user_id
      "UNIQUE_APP_ENDPOINT"        = var.unique_app_endpoint
      "UNIQUE_APP_ENDPOINT_SECRET" = var.unique_app_endpoint_secret

      # Zitadel settings
      "ZITADEL_BASE_URL"      = var.zitadel_base_url
      "ZITADEL_CLIENT_ID"     = var.zitadel_client_id
      "ZITADEL_CLIENT_SECRET" = var.zitadel_client_secret
    }
  }
}
