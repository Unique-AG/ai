# search-proxy-secrets

Terraform module that creates Azure Key Vault secret **placeholders** for Unique Search Proxy provider API keys.

Values are officiated manually after apply. Terraform ignores subsequent value changes via `lifecycle.ignore_changes`.

## Default placeholders

| Placeholder key             | Key Vault secret name                 | Env var (via ExternalSecret) |
| --------------------------- | ------------------------------------- | ---------------------------- |
| `perplexity-search-api-key` | `manual-perplexity-search-api-key`    | `PERPLEXITY_SEARCH_API_KEY`  |
| `brave-search-api-key`      | `manual-brave-search-api-key`         | `BRAVE_SEARCH_API_KEY`       |

The `manual-` prefix is added by this module.

## Usage

```hcl
module "search_proxy" {
  source       = "github.com/unique-ag/ai.git//connectors/unique_search_proxy/unique_search_proxy_client/deploy/terraform/azure/search-proxy-secrets?ref=<sha>"
  key_vault_id = data.azurerm_key_vault.core.id
  # secrets_placeholders defaults cover Perplexity + Brave
}
```
