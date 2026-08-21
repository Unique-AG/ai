data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                        = var.name
  location                    = var.location
  resource_group_name         = var.resource_group_name
  enabled_for_disk_encryption = true
  tenant_id                   = coalesce(var.tenant_id, data.azurerm_client_config.current.tenant_id)
  soft_delete_retention_days  = 7
  purge_protection_enabled    = true
  sku_name                    = "standard"
  rbac_authorization_enabled  = false
  tags                        = var.tags

  dynamic "access_policy" {
    for_each = var.keyvault_officer_object_ids
    content {
      tenant_id = coalesce(var.tenant_id, data.azurerm_client_config.current.tenant_id)
      object_id = access_policy.value
      key_permissions = [
        "Create",
        "Get",
        "List",
      ]
      secret_permissions = [
        "Set",
        "Get",
        "Delete",
        "Purge",
        "Recover",
        "List",
      ]
    }
  }

  dynamic "access_policy" {
    for_each = var.keyvault_reader_object_ids
    content {
      tenant_id = coalesce(var.tenant_id, data.azurerm_client_config.current.tenant_id)
      object_id = access_policy.value
      secret_permissions = [
        "Get",
        "List",
      ]
    }
  }
}

resource "azurerm_monitor_diagnostic_setting" "sentinel_audit" {
  count                      = var.sentinel_log_analytics_workspace_id != null ? 1 : 0
  name                       = "audit-to-sentinel"
  target_resource_id         = azurerm_key_vault.this.id
  log_analytics_workspace_id = var.sentinel_log_analytics_workspace_id

  enabled_log {
    category_group = "audit"
  }
}

resource "azurerm_key_vault_secret" "manual_secret" {
  for_each = {
    for key, value in var.secrets_placeholders : key => value
    if lookup(value, "create", true)
  }

  content_type    = lookup(each.value, "content_type", "text/plain")
  expiration_date = lookup(each.value, "expiration_date", "2099-12-31T23:59:59Z")
  key_vault_id    = azurerm_key_vault.this.id
  name            = "manual-${each.key}"
  value           = "<TO BE SET MANUALLY>"

  lifecycle {
    ignore_changes = [value, tags, content_type, expiration_date]
  }
}
