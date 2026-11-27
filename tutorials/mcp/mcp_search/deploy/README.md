# Deploying mcp_search

**App Service is the current, recommended, and supported deploy path.** Use it for
lab/demo and day-to-day deploys.

| Path | Status | Docs |
|------|--------|------|
| [`appservice/`](./appservice/) | **Supported** — one script builds via `az acr build`, deploys an App Service Web App pinned to the image digest, and pushes app/Zitadel secrets from local `unique.env` / `zitadel.env`. | [App Service guide](./appservice/README.md) |
| [`terraform/`](./terraform/) | **WIP / experimental** — Azure Container Instances IaC (Key Vault, ACR, Log Analytics, Caddy HTTPS). Not the primary path; expect gaps and churn. Prefer App Service unless you are intentionally working on this stack. | [Terraform guide](./terraform/README.md) |

Configure the App Service target via [`appservice/deploy.env`](./appservice/deploy.env.example) (copy from `deploy.env.example`) or environment variables (`SUBSCRIPTION`, `RG`, `APP`, `ACR`).

## Auth warning

Do **not** set `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` on a deployed app — those are for local unauthenticated testing only. Production identity comes from the logged-in OAuth user (JWT / userinfo) or Unique AI `_meta`. See [Per-user identity](../README.md#per-user-identity-not-a-fixed-service-user) in the package README.

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) (`az login`)
- An Azure subscription and resource group with permission to create resources
- Filled-in Unique + Zitadel credentials at the package root (see [`unique.env.example`](../unique.env.example) / [`zitadel.env.example`](../zitadel.env.example))
- Terraform path (WIP) additionally needs [Terraform](https://www.terraform.io/downloads) >= 1.5.0 and [Docker](https://docs.docker.com/get-docker/)
