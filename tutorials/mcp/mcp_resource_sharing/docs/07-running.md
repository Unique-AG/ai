# 07 — Running the Demo

> **Previous**: [06 — Security model](06-security.md)
> **Next**: [08 — IdP stack (Keycloak + Dex)](08-compose.md)

---

## Code layout

The code is split by domain so producer and consumer concerns stay separate,
with a `common/` package for things neither domain owns alone:

```
mcp_resource_sharing/
├── pyproject.toml          # uv project manifest
├── src/mcp_resource_sharing/
│   ├── common/             # shared, domain-agnostic building blocks
│   │   ├── env.py          # compose/.env path + settings_config() helper
│   │   ├── clients.py      # OAuth client registry (RP_CLIENT_*)
│   │   ├── oauth.py        # RFC 8693 wire constants (not config)
│   │   ├── identity.py     # current_subject() from the verified token
│   │   ├── logging_setup.py
│   │   └── token_exchange.py  # client-side discovery + exchange
│   ├── producer/           # producer security domain
│   │   ├── settings.py     # producer URLs, JWKS, audience (RP_PRODUCER_*)
│   │   └── server.py       # the resource server (notes)
│   ├── consumer/           # consumer security domain
│   │   ├── settings.py     # consumer URLs, allowlist (RP_CONSUMER_*)
│   │   └── server.py       # the archiver
│   └── demo/
│       └── run_demo.py     # end-to-end scenario script
│
└── compose/
    ├── docker-compose.yml  # Dex, Keycloak, MCP servers, demo runner
    ├── Dockerfile
    ├── .env                # shared env for all containers
    ├── dex/config.yaml     # consumer IdP (Dex)
    └── keycloak/           # producer realm import + post-setup script
```

**Dependency rule**: code only imports *into* `common`, never across domains.
The consumer never imports anything producer-specific. Federation and token
exchange are configured in Keycloak (`compose/keycloak/`), not in Python.

---

## Starting the stack

Run from the `mcp_resource_sharing/` directory:

```bash
uv sync
docker compose -f compose/docker-compose.yml up --build
docker compose -f compose/docker-compose.yml logs -f demo
```

Services start in order: Dex → Keycloak (realm import) → `keycloak-setup`
(FGAP permissions) → producer + consumer → demo.

Expected output:

```
[dex] alice token  sub='...'  preferred_username='alice'
[keycloak] alice producer token  sub='<uuid>'  aud=['http://producer:8001/mcp', ...]
[alice] created note://...  (owner_sub='<uuid>')
[alice] archived: {'producer': 'http://producer:8001/mcp', ...}
[bob] denied as expected: ...access denied: user '<bob-uuid>' is not the owner ...
✓ Demo completed successfully
```

For a clean slate after realm config changes:

```bash
docker compose -f compose/docker-compose.yml down
docker compose -f compose/docker-compose.yml up --build
```

---

## Configuration reference

All settings are loaded from `compose/.env` (or environment variables) with no
hardcoded values in application logic. Container-specific overrides are set in
`docker-compose.yml`.

| Variable | Default (compose) | Purpose |
|----------|-------------------|---------|
| `FASTMCP_HOST` | `0.0.0.0` | Bind MCP HTTP servers on all interfaces inside Docker |
| `RP_PRODUCER_BASE_URL` | `http://producer:8001` | Producer server public URL |
| `RP_PRODUCER_IDP_ISSUER` | `http://keycloak:8080/realms/producer` | Producer IdP issuer |
| `RP_PRODUCER_IDP_JWKS_URI` | Keycloak certs URL | JWKS for 🟣 token verification |
| `RP_PRODUCER_AUDIENCE` | _(canonical MCP URL)_ | Override audience if AS uses a different value |
| `RP_CONSUMER_BASE_URL` | `http://consumer:8002` | Consumer server public URL |
| `RP_CONSUMER_IDP_ISSUER` | `http://dex:5556` | Consumer IdP issuer |
| `RP_CONSUMER_IDP_JWKS_URI` | `http://dex:5556/keys` | JWKS for 🔵 token verification |
| `RP_CONSUMER_AUDIENCE` | `alice-desktop-app` | Dex puts client id in `aud`, not MCP URL |
| `RP_CONSUMER_ALLOWED_PRODUCERS` | `http://producer:8001/mcp` | Comma-separated producer allowlist |
| `RP_CLIENT_DEMO_APP_ID` | `alice-desktop-app` | OAuth client for the demo script |
| `RP_CLIENT_CONSUMER_SERVICE_ID` | `resource-consumer-service` | OAuth client for the consumer server |
| `RP_TOKEN_EXCHANGE_SUBJECT_ISSUER` | `dex` | Keycloak legacy exchange: Dex IdP alias |
| `RP_TOKEN_EXCHANGE_AUDIENCE` | `resource-producer` | Keycloak legacy exchange: target client id |

---

## Demo simplifications vs. production

| Demo | Production |
|------|------------|
| Dex password grant for demo users | Authorization Code + PKCE (or device code); disable ROPC |
| Keycloak `start-dev` + H2 | `start` with external PostgreSQL, TLS at the edge |
| Legacy token exchange V1 + FGAP v1 | Plan migration to Standard Token Exchange V2 when external→internal is supported |
| Public exchange clients | Confidential clients with `private_key_jwt` or mTLS |
| `configure-realm.sh` sidecar | Terraform, `keycloak-config-cli`, or Operator-managed realm |
| Dex `aud` = client id, not MCP URL | IdP with RFC 8707 resource indicators, or audience mapper |

What carries over **unchanged**: the discovery ladder, the exchange checks, the
audience binding on 🟣 tokens, the `act` audit claim, and the rule that
authorization is enforced at the resource on a verified `sub`.

---

> **Next**: [08 — IdP stack (Keycloak + Dex)](08-compose.md) — realm
> configuration, token flow, and Keycloak token-exchange wiring.
