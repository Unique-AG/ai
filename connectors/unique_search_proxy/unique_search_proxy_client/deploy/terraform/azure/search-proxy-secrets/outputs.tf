output "secret_names" {
  description = "The names of the created Key Vault secrets."
  value       = [for secret in azurerm_key_vault_secret.manual_secret : secret.name]
}
