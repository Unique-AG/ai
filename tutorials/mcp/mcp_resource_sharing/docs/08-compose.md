# 08 — IdP Stack (Keycloak + Dex)

> **Previous**: [07 — Running the demo](07-running.md)
> **Next**: [09 — Lessons learned](09-lessons-learned-compose.md)

---

The stack uses two production-grade, self-hostable identity providers alongside
the same MCP server code:

| Component | Provider | Role |
|-----------|----------|------|
| Consumer IdP | **[Dex](https://dexidp.io)** | Lightweight OIDC, static users, single YAML config |
| Producer IdP | **[Keycloak](https://www.keycloak.org)** 26 | Enterprise AS, realm import, token exchange + federation |

---

## Why Dex for the consumer and Keycloak for the producer?

**Dex** represents a *simple, consumer-side* IdP where the organisation
controls its users but doesn't need a full AS. A single YAML file is the
entire configuration.

**Keycloak** represents the *resource-owning* organisation that must:
1. **Trust** tokens from external organisations (Dex is registered as an IdP).
2. **Exchange** those tokens for narrowly-scoped, audience-bound producer tokens.
3. **Enforce** which clients are allowed to exchange (fine-grained policy).

---

## Architecture

```mermaid
flowchart LR
    subgraph CD["Consumer domain"]
        ALICE["Alice / Bob"]:::person
        DEX["Dex\nhttp://dex:5556"]:::idp
        CON["Consumer server\nhttp://consumer:8002"]:::consumer
    end

    subgraph PD["Producer domain"]
        KC["Keycloak\nhttp://keycloak:8080/realms/producer"]:::idp
        PRO["Producer server\nhttp://producer:8001"]:::producer
    end

    ALICE -- "password grant\n(demo only)" --> DEX
    ALICE -- "Bearer 🔵 Dex token" --> CON
    CON -- "OIDC discovery + JWKS\n(to verify 🔵)" --> DEX
    CON -- "RFC 8693 exchange\n(subject_token = 🔵)" --> KC
    KC -- "IdP federation\n(OIDC + JWKS, to verify 🔵)" --> DEX
    CON -- "Bearer 🟣 Keycloak token" --> PRO
    PRO -- "OIDC discovery + JWKS\n(to verify 🟣)" --> KC

    classDef person fill:none,stroke:#888
    classDef idp fill:none,stroke:#e67e22,stroke-width:2px
    classDef consumer fill:none,stroke:#2980b9,stroke-width:2px
    classDef producer fill:none,stroke:#8e44ad,stroke-width:2px
    style CD fill:none,stroke:#2980b9,stroke-width:2px
    style PD fill:none,stroke:#8e44ad,stroke-width:2px
```

---

## Token flow

```mermaid
sequenceDiagram
    autonumber
    box Consumer domain 🔵
        participant A as Alice
        participant C as Consumer :8002
    end
    box Producer domain 🟣
        participant D as Dex :5556
        participant K as Keycloak :8080
        participant P as Producer :8001
    end

    Note over A: needs a 🔵 Dex token first
    A->>D: POST /token<br/>grant=password, client_id=alice-desktop-app<br/>username=alice@consumer.local, password=alice123
    D-->>A: 🔵 alice_dex_token<br/>aud=alice-desktop-app · iss=dex:5556

    A->>C: tools/call archive_note(producer_url, uri)<br/>Bearer 🔵 alice_dex_token
    Note over C: verify 🔵 against Dex JWKS<br/>sub=alice · producer on allowlist? ✓

    Note over C,P: Phase 1 — discover the producer's IdP (RFC 9728)
    C->>P: GET /mcp  (no token)
    P-->>C: 401 · WWW-Authenticate: resource_metadata="…"
    C->>P: GET /.well-known/oauth-protected-resource/mcp
    P-->>C: { authorization_servers: ["http://keycloak:8080/realms/producer"] }
    C->>K: GET /realms/producer/.well-known/oauth-authorization-server
    K-->>C: { token_endpoint: "…/protocol/openid-connect/token" }

    Note over C,K: Phase 2 — token exchange: 🔵 ➜ 🟣 (RFC 8693 + RFC 8707)
    C->>K: POST /token<br/>grant=token-exchange · subject_token=🔵<br/>resource=http://producer:8001/mcp · client_id=resource-consumer-service<br/>subject_issuer=dex · audience=resource-producer
    Note over K: validate 🔵 against Dex JWKS ✓<br/>resource-consumer-service in policy ✓<br/>audience mapper → aud=producer:8001/mcp
    K-->>C: 🟣 alice_kc_token<br/>sub=keycloak_alice_uuid · aud=http://producer:8001/mcp · act.sub=resource-consumer-service

    Note over C,P: Phase 3 — authorised read
    C->>P: resources/read note://{id}<br/>Bearer 🟣 alice_kc_token
    Note over P: verify 🟣 against Keycloak JWKS ✓<br/>note.owner == sub (keycloak_alice_uuid)? ✓
    P-->>C: note content
    C-->>A: archived ✓
```

> 🔵 Dex token — `iss=http://dex:5556`, `aud=alice-desktop-app`
> 🟣 Keycloak token — `iss=http://keycloak:8080/realms/producer`, `aud=http://producer:8001/mcp`

---

## How Keycloak token exchange is configured

`compose/keycloak/producer-realm.json` wires the declarative baseline; the
`keycloak-setup` service runs `configure-realm.sh` to attach FGAP v1 permissions
that realm JSON alone cannot express:

```
resource-producer client
  authorizationServicesEnabled: true
  │
  ├── resource: token-exchange  (type=urn:ietf:params:oauth:token-type:access_token)
  │
  ├── policy: consumer-clients-can-exchange
  │     type=client, grants: [resource-consumer-service, alice-desktop-app]
  │
  └── permission: token-exchange.permission.client.resource-producer
        resources=[token-exchange]  scopes=[token-exchange]
        policies=[consumer-clients-can-exchange]

  protocolMapper: producer-mcp-url-audience
    → stamps aud="http://producer:8001/mcp" on every exchanged access token

identityProvider: dex
  discoveryEndpoint=http://dex:5556/.well-known/openid-configuration
  → Keycloak validates Dex JWKS at exchange time
  → first exchange creates a federated Keycloak user for alice/bob
```

Keycloak requires `--features=token-exchange,admin-fine-grained-authz:v1` for
legacy external→internal exchange (Dex 🔵 in, Keycloak 🟣 out).

---

## Notable implementation details

| Topic | Detail |
|-------|--------|
| 🔵 consumer token `aud` | `alice-desktop-app` — Dex has no RFC 8707 resource indicators; set `RP_CONSUMER_AUDIENCE` |
| 🟣 producer token `aud` | Keycloak **Audience protocol mapper** stamps `http://producer:8001/mcp` |
| `sub` in 🟣 token | Keycloak federated **UUID**; `preferred_username` used for display |
| Exchange client auth | Keycloak **fine-grained authorization policy** on `realm-management` |
| IdP federation | Dex registered as OIDC IdP; Keycloak validates JWKS at runtime |
| Exchange parameters | Legacy V1 needs `subject_issuer=dex` and `audience=resource-producer` |

---

## Configuration gotchas

See **[09 — Lessons learned](09-lessons-learned-compose.md)** for the full
diagnostic tables. Short list:

| Topic | Detail |
|-------|--------|
| `start-dev` only | `--import-realm` works with `start-dev`. For production use `kc.sh import` or the Admin REST API. |
| Post-import setup | FGAP v1 token-exchange permissions require `keycloak-setup` / `configure-realm.sh` — realm JSON alone is insufficient. |
| Exchange parameters | Legacy V1 needs `subject_issuer=dex` and `audience=resource-producer` (see `compose/.env`). |
| Exchange client auth | Both exchange clients are **public** in this demo. In production make them confidential (`private_key_jwt`, mTLS). |
| Audience binding gap | Dex 🔵 tokens carry `aud=alice-desktop-app`, not the consumer MCP URL. Set via `RP_CONSUMER_AUDIENCE`. |
| Issuer trailing slash | Pydantic normalizes `http://dex:5556` → `http://dex:5556/`; consumer JWT verification strips it via `idp_issuer_value`. |

---

> **Next**: [09 — Lessons learned](09-lessons-learned-compose.md) — failure
> modes and diagnostics from standing up the stack.
