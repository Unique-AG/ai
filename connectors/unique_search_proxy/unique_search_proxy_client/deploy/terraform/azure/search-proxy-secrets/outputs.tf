output "key_vault_id" {
  description = "Resource ID of the dedicated search-proxy Key Vault."
  value       = azurerm_key_vault.this.id
}

output "key_vault_name" {
  description = "Name of the dedicated search-proxy Key Vault."
  value       = azurerm_key_vault.this.name
}

output "vault_uri" {
  description = "URI of the dedicated search-proxy Key Vault (for External Secrets SecretStore)."
  value       = azurerm_key_vault.this.vault_uri
}

output "secret_names" {
  description = "Names of the created Key Vault secrets."
  value       = [for secret in azurerm_key_vault_secret.manual_secret : secret.name]
}
