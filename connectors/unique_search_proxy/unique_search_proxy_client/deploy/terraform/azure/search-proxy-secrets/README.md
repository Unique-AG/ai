# search-proxy-secrets

Terraform module that creates a **dedicated Azure Key Vault** for Unique Search Proxy and
manual API-key placeholders inside it.

This does **not** replace legacy secrets in shared vaults (`kv-core` / `kv-app-common`).
Those remain until assistants-core and ExternalSecret cut over to this vault.

## Resources

- `azurerm_key_vault` — dedicated vault (access policies for officers + readers)
- `azurerm_key_vault_secret` placeholders (values officiated manually; TF ignores value changes)

## Default placeholders

| Placeholder key             | Key Vault secret name              | Env var (later via ESO)     |
| --------------------------- | ---------------------------------- | --------------------------- |
| `google-search-api-key`     | `manual-google-search-api-key`     | `GOOGLE_SEARCH_API_KEY`     |
| `brave-search-api-key`      | `manual-brave-search-api-key`      | `BRAVE_SEARCH_API_KEY`      |
| `perplexity-search-api-key` | `manual-perplexity-search-api-key` | `PERPLEXITY_SEARCH_API_KEY` |
| `tavily-api-key`            | `manual-tavily-api-key`            | `TAVILY_API_KEY`            |
| `jina-api-key`              | `manual-jina-api-key`              | `JINA_API_KEY`              |
| `firecrawl-api-key`         | `manual-firecrawl-api-key`         | `FIRECRAWL_API_KEY`         |

## Usage

```hcl
module "search_proxy" {
  source = "github.com/unique-ag/ai.git//connectors/unique_search_proxy/unique_search_proxy_client/deploy/terraform/azure/search-proxy-secrets?ref=<sha>"

  name                = "qa-search-proxy"
  resource_group_name = module.core-infra.resource_group_name # or data.azurerm_resource_group.core.name
  location            = var.azure_location
  keyvault_officer_object_ids = [
    "…", # Role Developer (tf)
    "…", # Atlantis
  ]
  keyvault_reader_object_ids = [
    module.core-infra.aks_key_vault_secrets_provider_secret_identity_object_id,
    module.workload_identities.user_assigned_identity_object_ids["search-proxy"],
  ]
  sentinel_log_analytics_workspace_id = var.sentinel_log_analytics_workspace_id
}
```

## Follow-up (not this module)

1. Officiate real API key values in the new vault.
2. Add a namespace `SecretStore` (`kv-search-proxy`) and point search-proxy `ExternalSecret` at it.
3. Later remove duplicates from shared vaults once assistants-core no longer needs them.
