# ============================================================================
# Input Variables
# ============================================================================

variable "subscription_id" {
  description = "Azure Subscription ID (optional - will use default from Azure CLI if not specified)"
  type        = string
  default     = null
}

variable "resource_group_name" {
  description = "The name of the resource group where resources will be deployed"
  type        = string
}

variable "location" {
  description = "The Azure region where resources will be deployed"
  type        = string
}

variable "base_name" {
  description = "Base name for resources (used in naming conventions)"
  type        = string
}

variable "base_name_clean" {
  description = "Base name without hyphens (for resources that don't allow hyphens)"
  type        = string
}

variable "domain_name" {
  description = "The domain name for the application (used for Caddy/Let's Encrypt)"
  type        = string
}

variable "caddy_email" {
  description = "Email address for Let's Encrypt certificate notifications"
  type        = string
}

# ============================================================================
# Application Secrets (stored in Key Vault)
# ============================================================================

variable "unique_app_key" {
  description = "UNIQUE_APP_KEY environment variable"
  type        = string
  sensitive   = true
}

variable "unique_app_id" {
  description = "UNIQUE_APP_ID environment variable"
  type        = string
  sensitive   = true
}

variable "unique_api_base_url" {
  description = "UNIQUE_API_BASE_URL environment variable"
  type        = string
}

variable "unique_auth_company_id" {
  description = "UNIQUE_AUTH_COMPANY_ID environment variable"
  type        = string
  sensitive   = true
}

variable "unique_auth_user_id" {
  description = "UNIQUE_AUTH_USER_ID environment variable"
  type        = string
  sensitive   = true
}

variable "unique_app_endpoint" {
  description = "UNIQUE_APP_ENDPOINT environment variable"
  type        = string
}

variable "unique_app_endpoint_secret" {
  description = "UNIQUE_APP_ENDPOINT_SECRET environment variable"
  type        = string
  sensitive   = true
}

variable "zitadel_base_url" {
  description = "ZITADEL_BASE_URL environment variable"
  type        = string
}

variable "zitadel_client_id" {
  description = "ZITADEL_CLIENT_ID environment variable"
  type        = string
  sensitive   = true
}

variable "zitadel_client_secret" {
  description = "ZITADEL_CLIENT_SECRET environment variable"
  type        = string
  sensitive   = true
}

# ============================================================================
# Optional Variables
# ============================================================================

variable "app_container_cpu" {
  description = "CPU cores for the application container"
  type        = number
  default     = 1
}

variable "app_container_memory" {
  description = "Memory in GB for the application container"
  type        = number
  default     = 1.5
}

variable "caddy_container_cpu" {
  description = "CPU cores for the Caddy container"
  type        = number
  default     = 0.5
}

variable "caddy_container_memory" {
  description = "Memory in GB for the Caddy container"
  type        = number
  default     = 0.5
}

variable "app_image_tag" {
  description = "Docker image tag for the application"
  type        = string
  default     = "latest"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    project    = "mcp-search"
    managed_by = "terraform"
  }
}

variable "use_managed_identity_for_acr" {
  description = "Use managed identity for ACR access (requires role assignment permissions). If false, uses admin credentials."
  type        = bool
  default     = true
}

variable "grant_rg_user_access_admin" {
  description = "Grant User Access Administrator role at resource group level (requires Contributor or Owner permissions)"
  type        = bool
  default     = false
}

variable "use_staging_letsencrypt" {
  description = "Use Let's Encrypt staging environment (default: true). Staging certificates are NOT trusted but allow unlimited requests for testing."
  type        = bool
  default     = true
}

