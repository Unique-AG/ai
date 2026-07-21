# Deploying mcp_search

Two self-contained options:

- [`appservice/`](./appservice) — **fast lab/demo path** (default). One script:
  builds the image with `az acr build`, deploys an Azure App Service Web App
  pinned to the image digest, and pushes app/Zitadel secrets from your local
  `unique.env`/`zitadel.env`. Configure the target via `appservice/deploy.env`
  (copy from `deploy.env.example`) or environment variables.
- [`terraform/`](./terraform) — **standalone IaC example**: full Azure Container
  Instances stack (Key Vault, ACR, Log Analytics, Caddy-managed HTTPS) with
  remote-state support. Frozen as a reference; see its README.

Whichever path you use, do **not** set `UNIQUE_AUTH_USER_ID` /
`UNIQUE_AUTH_COMPANY_ID` on a deployed app — identity comes from the
logged-in OAuth user (see the package README, "Identity Resolution").
