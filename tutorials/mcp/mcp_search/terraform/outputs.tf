# ============================================================================
# Outputs
# ============================================================================

output "resource_group_name" {
  description = "The name of the resource group"
  value       = data.azurerm_resource_group.main.name
}

output "location" {
  description = "The Azure region where resources are deployed"
  value       = var.location
}

# ============================================================================
# Container Registry Outputs
# ============================================================================

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "The login server URL for the Azure Container Registry"
  value       = azurerm_container_registry.main.login_server
}

output "acr_admin_username" {
  description = "The admin username for the Azure Container Registry"
  value       = azurerm_container_registry.main.admin_username
  sensitive   = true
}

# ============================================================================
# Key Vault Outputs
# ============================================================================

output "key_vault_name" {
  description = "The name of the Azure Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "The URI of the Azure Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

# ============================================================================
# Storage Account Outputs
# ============================================================================

output "storage_account_name" {
  description = "The name of the Storage Account (used for Caddy certificates and Terraform backend)"
  value       = azurerm_storage_account.main.name
}

output "storage_account_for_backend" {
  description = "Storage account details for Terraform backend configuration"
  value = {
    resource_group_name  = data.azurerm_resource_group.main.name
    storage_account_name = azurerm_storage_account.main.name
    container_name       = azurerm_storage_container.tfstate.name
  }
}

# ============================================================================
# Container Instance Outputs
# ============================================================================

output "aci_name" {
  description = "The name of the Azure Container Instance"
  value       = azurerm_container_group.main.name
}

output "aci_fqdn" {
  description = "The FQDN of the Azure Container Instance"
  value       = azurerm_container_group.main.fqdn
}

output "aci_ip_address" {
  description = "The public IP address of the Azure Container Instance"
  value       = azurerm_container_group.main.ip_address
}

# ============================================================================
# Application URLs
# ============================================================================

output "application_url" {
  description = "The URL to access the application (after DNS configuration)"
  value       = "https://${var.domain_name}"
}

output "aci_direct_url" {
  description = "Direct URL to access via ACI (for testing before DNS setup)"
  value       = "http://${azurerm_container_group.main.fqdn}"
}

# ============================================================================
# Docker Commands
# ============================================================================

output "docker_login_command" {
  description = "Command to login to the Azure Container Registry"
  value       = "az acr login --name ${azurerm_container_registry.main.name}"
}

output "docker_build_and_push_command" {
  description = "Commands to build and push the Docker image"
  value       = <<-EOF
    # Build the Docker image
    docker build -t ${azurerm_container_registry.main.login_server}/mcp-search:latest .

    # Push to ACR
    docker push ${azurerm_container_registry.main.login_server}/mcp-search:latest

    # Or use ACR Tasks to build directly in Azure:
    az acr build --registry ${azurerm_container_registry.main.name} --image mcp-search:latest .
  EOF
}

# ============================================================================
# DNS Configuration
# ============================================================================

output "dns_configuration" {
  description = "DNS record to create for your domain"
  value       = <<-EOF
    Create an A record pointing to the container IP:
      ${var.domain_name} -> ${azurerm_container_group.main.ip_address}

    Or create a CNAME record:
      ${var.domain_name} -> ${azurerm_container_group.main.fqdn}
  EOF
}
