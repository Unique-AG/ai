# search-proxy-secrets

Terraform module that creates Azure Key Vault secret **placeholders** for Unique Search Proxy provider API keys.

Values are officiated manually after apply. Terraform ignores subsequent value changes via `lifecycle.ignore_changes`.

## Default placeholders

| Placeholder key             | Key Vault secret name              | Env var (via ExternalSecret) |
| --------------------------- | ---------------------------------- | ---------------------------- |
| `google-search-api-key`     | `manual-google-search-api-key`     | `GOOGLE_SEARCH_API_KEY`      |
| `brave-search-api-key`      | `manual-brave-search-api-key`      | `BRAVE_SEARCH_API_KEY`       |
| `perplexity-search-api-key` | `manual-perplexity-search-api-key` | `PERPLEXITY_SEARCH_API_KEY`  |
| `tavily-api-key`            | `manual-tavily-api-key`            | `TAVILY_API_KEY`             |
| `jina-api-key`              | `manual-jina-api-key`              | `JINA_API_KEY`               |
| `firecrawl-api-key`         | `manual-firecrawl-api-key`         | `FIRECRAWL_API_KEY`          |

The `manual-` prefix is added by this module.

During migration, tenants may still create `google` / `tavily` / `jina` / `firecrawl`
via the legacy secrets bundle / `common_secret_placeholders` for assistants-core.
In that case, pass `secrets_placeholders` with only the new keys (e.g. Brave + Perplexity)
so Terraform does not try to create the same Key Vault secret twice.

## Usage

```hcl
module "search_proxy" {
  source       = "github.com/unique-ag/ai.git//connectors/unique_search_proxy/unique_search_proxy_client/deploy/terraform/azure/search-proxy-secrets?ref=<sha>"
  key_vault_id = data.azurerm_key_vault.core.id
  # While assistants-core still uses the legacy path for google/tavily/jina/firecrawl:
  secrets_placeholders = {
    perplexity-search-api-key = { create = true }
    brave-search-api-key      = { create = true }
  }
}
```
