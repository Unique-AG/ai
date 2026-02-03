# ============================================================================
# Identity and Access Management
# Depends on: foundation.tf, key-vault.tf, container-registry.tf
# ============================================================================

# User Assigned Managed Identity for ACI
resource "azurerm_user_assigned_identity" "aci" {
  name                = "id-${local.base_name}-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  tags = var.tags
}

# Grant current user User Access Administrator at resource group level (optional)
# This allows creating role assignments within the resource group
resource "azurerm_role_assignment" "rg_user_access_admin" {
  count                = var.grant_rg_user_access_admin ? 1 : 0
  scope                = data.azurerm_resource_group.main.id
  role_definition_name = "User Access Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Grant the managed identity access to Key Vault secrets
resource "azurerm_key_vault_access_policy" "aci" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_user_assigned_identity.aci.principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

# Grant the managed identity access to pull from ACR (optional)
# This requires User Access Administrator permissions at the resource group level
resource "azurerm_role_assignment" "acr_pull" {
  count                = var.use_managed_identity_for_acr ? 1 : 0
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aci.principal_id

  # Wait for role assignment permission to be granted if enabled
  depends_on = [azurerm_role_assignment.rg_user_access_admin]
}
