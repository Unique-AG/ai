# 04 — End-to-End Flow

> **Previous**: [03 — Trust and architecture](03-trust.md)
> **Next**: [05 — Exchange and denial](05-exchange.md)

---

## Alice archives her note — full sequence

```mermaid
sequenceDiagram
    autonumber
    box Consumer domain 🔵
        participant U as Alice's host app
        participant C as Consumer :8002
    end
    box Producer domain 🟣
        participant P as Producer :8001
        participant K as Keycloak :8080
        participant D as Dex :5556
    end

    Note over U: holds 🔵 (sub=alice)
    U->>C: tools/call archive_note(producer_url, uri)<br/>Bearer 🔵
    Note over C: verify 🔵 (sig, iss, aud=client id)<br/>producer_url on allowlist? ✓

    Note over C,K: Phase 1 — discover the producer's IdP (no prior knowledge, no tokens involved)
    C->>P: GET /mcp (no token)
    P-->>C: 401 + WWW-Authenticate: resource_metadata="…"
    C->>P: GET /.well-known/oauth-protected-resource/mcp
    P-->>C: { authorization_servers: ["http://keycloak:8080/realms/producer"] }
    C->>K: GET /.well-known/oauth-authorization-server
    K-->>C: { token_endpoint: "…/protocol/openid-connect/token" }

    Note over C,K: Phase 2 — token exchange: 🔵 ➜ 🟣 (RFC 8693 + RFC 8707)
    C->>K: POST /token<br/>grant=token-exchange, subject_token=🔵,<br/>resource=producer URL, client_id=consumer,<br/>subject_issuer=dex, audience=resource-producer
    Note over K: client in policy? ✓<br/>resource known? ✓<br/>🔵 verifies against Dex JWKS? ✓
    K-->>C: 🟣 (sub=keycloak_uuid, aud=producer URL, act=consumer)

    Note over C,P: Phase 3 — authorized read + archive
    C->>P: resources/read note://{id}<br/>Bearer 🟣
    Note over P: verify 🟣 (sig, iss, aud=own URL)<br/>note.owner == sub (keycloak_uuid)? ✓
    P-->>C: note content
    C->>C: INSERT INTO archived_notes
    C-->>U: archived ✓
```

Note what the consumer needed in advance: **nothing producer-specific except
the allowlist entry**. The producer URL arrives as a tool argument; the IdP,
its token endpoint, and the 🟣 audience are all derived at runtime from that
URL alone — no 🟣 token details are pre-configured.

---

## Phase 1 in depth — the discovery ladder

The MCP 2025-11-25 revision made the `WWW-Authenticate` hint optional and
mandated client-side fallbacks. `common/token_exchange.py` implements the full
ladder:

```mermaid
flowchart TD
    A["GET producer URL, unauthenticated → 401"]:::probe --> B{"WWW-Authenticate has\nresource_metadata?"}:::probe
    B -- yes --> C["GET that URL"]:::prm
    B -- no --> D["GET {origin}/.well-known/\noauth-protected-resource{path}"]:::prm
    D -- 200 --> E
    D -- miss --> D2["GET {origin}/.well-known/\noauth-protected-resource"]:::prm
    D2 -- 200 --> E
    C --> E["RFC 9728 metadata:\nauthorization_servers = [issuer]"]:::prm
    E --> F["GET {issuer}/.well-known/\noauth-authorization-server"]:::asmeta
    F -- 200 --> H
    F -- miss --> G["GET {issuer}/.well-known/\nopenid-configuration"]:::asmeta
    G -- 200 --> H["RFC 8414 / OIDC metadata:\ntoken_endpoint"]:::asmeta
    H --> I["POST token exchange: 🔵 ➜ 🟣"]:::xchg

    classDef probe fill:none,stroke:#95a5a6
    classDef prm fill:none,stroke:#2980b9,stroke-width:2px
    classDef asmeta fill:none,stroke:#e67e22,stroke-width:2px
    classDef xchg fill:none,stroke:#8e44ad,stroke-width:2px
```

The implementation in `common/token_exchange.py`:

```python
async def _discover_token_endpoint(http, producer_url):
    # Step 1: probe → 401, check for resource_metadata in WWW-Authenticate
    probe = await http.get(producer_url)
    challenge = probe.headers.get("WWW-Authenticate", "")
    match = _RESOURCE_METADATA_RE.search(challenge)
    if match:
        metadata_urls = [match.group(1)]
    else:
        metadata_urls = _well_known_prm_urls(producer_url)  # RFC 9728 fallbacks

    # Step 2: fetch protected-resource metadata → authorization_servers
    resource_metadata = await _fetch_first_json(http, metadata_urls)
    issuer = resource_metadata["authorization_servers"][0].rstrip("/")

    # Step 3: fetch AS metadata → token_endpoint (RFC 8414 then OIDC fallback)
    as_metadata = await _fetch_first_json(http, [
        f"{issuer}/.well-known/oauth-authorization-server",
        f"{issuer}/.well-known/openid-configuration",
    ])
    return as_metadata["token_endpoint"]
```

Two IdPs, two roles:

- **Keycloak (producer IdP)** is discoverable — its issuer is a reachable URL
  serving RFC 8414/OIDC metadata because remote clients must find it at runtime
  to exchange 🔵→🟣.
- **Dex (consumer IdP)** is configured out of band — the consumer verifies 🔵
  tokens against Dex JWKS; users obtain 🔵 tokens via Dex's token endpoint
  (password grant in the demo only).

---

## Phase 2 in depth — what the exchange request carries

```
POST /realms/producer/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type           = urn:ietf:params:oauth:grant-type:token-exchange
subject_token        = <alice's 🔵 Dex JWT>
subject_token_type   = urn:ietf:params:oauth:token-type:access_token
requested_token_type = urn:ietf:params:oauth:token-type:access_token
resource             = http://producer:8001/mcp    ← RFC 8707 indicator
audience             = resource-producer           ← Keycloak legacy exchange
subject_issuer       = dex                         ← Keycloak legacy exchange
client_id            = resource-consumer-service
```

Keycloak legacy exchange uses `audience` for the target OAuth **client id** and
`subject_issuer` for the federated IdP alias. The `resource` parameter still
names the MCP URL for RFC 8707; Keycloak's audience mapper stamps that URL into
the minted 🟣 token's `aud` claim.

---

> **Next**: [05 — Exchange checks and the denial path](05-exchange.md) — the
> four checks Keycloak runs, and what happens when Bob tries to archive Alice's
> note.
