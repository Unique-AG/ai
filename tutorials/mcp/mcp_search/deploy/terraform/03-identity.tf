# ============================================================================
# Identity and Access Management
# Depends on: foundation.tf, key-vault.tf, container-registry.tf
# ============================================================================

# User Assigned Managed Identity for ACI
resource "azurerm_user_assigned_identity" "aci" {
  name                = "id-${var.base_name}-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = var.location

  tags = var.tags
}

# Grant the managed identity access to Key Vault secrets via RBAC
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.aci.principal_id
}

# Grant the managed identity access to pull from ACR (optional)
resource "azurerm_role_assignment" "acr_pull" {
  count                = var.use_managed_identity_for_acr ? 1 : 0
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aci.principal_id
}
