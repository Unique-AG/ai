variable "name" {
  description = "Name of the dedicated search-proxy Key Vault (3-24 chars, globally unique)."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group for the Key Vault."
  type        = string
}

variable "location" {
  description = "Azure region for the Key Vault."
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID. Defaults to the current provider tenant."
  type        = string
  default     = null
}

variable "keyvault_officer_object_ids" {
  description = "Object IDs granted Key Vault Secrets Officer-style access policies (set/get/list/delete)."
  type        = list(string)
}

variable "keyvault_reader_object_ids" {
  description = "Object IDs granted Get/List on secrets (AKS secrets provider, workload identities)."
  type        = list(string)
  default     = []
}

variable "sentinel_log_analytics_workspace_id" {
  description = "Optional Log Analytics workspace for Key Vault audit diagnostics."
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to the Key Vault."
  type        = map(string)
  default     = {}
}

variable "secrets_placeholders" {
  description = "Map of secrets that are manually created in this vault. The manual- prefix is prepended automatically."
  type = map(object({
    create          = optional(bool, true)
    expiration_date = optional(string, "2099-12-31T23:59:59Z")
  }))
  default = {
    google-search-api-key     = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
    brave-search-api-key      = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
    perplexity-search-api-key = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
    tavily-api-key            = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
    jina-api-key              = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
    firecrawl-api-key         = { create = true, expiration_date = "2099-12-31T23:59:59Z" }
  }
}
