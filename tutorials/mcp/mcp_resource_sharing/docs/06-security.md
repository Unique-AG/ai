# 06 — Security Model

> **Previous**: [05 — Exchange checks and denial](05-exchange.md)
> **Next**: [07 — Running the demo](07-running.md)

---

## Defense in depth — threat → control

| Threat | Control | Where |
|--------|---------|-------|
| Forwarding a 🔵 user token to the producer (passthrough) | Audience binding: `aud` = canonical MCP URL, verified on every request | `JWTVerifier(audience=…)` in both servers |
| Replaying a 🔵/🟣 token against the wrong server | Same — each token names exactly one resource | RFC 8707 `resource` → `aud` mapping in the IdP |
| Stranger fabricating 🟣 producer tokens | Keycloak client policy + (in production) confidential-client authentication | `compose/keycloak/` FGAP policies |
| Registered client requesting 🟣 tokens for arbitrary targets | `invalid_target` on unknown `resource` | Exchange check 3 |
| Consumer as credentialed SSRF proxy (confused deputy) | Producer allowlist in operator config — consumer only attaches a 🟣 credential to allowlisted URLs | `RP_CONSUMER_ALLOWED_PRODUCERS` |
| Client lying about identity (e.g. via `_meta`) | Identity *only* from the verified 🟣 token's `sub` | `common/identity.py` |
| Enumerating other users' notes | Resource **template** — notes never appear in `resources/list` | `@mcp.resource("note://{note_id}")` |
| Learning who owns a note from the error | Denial message omits the owner | `producer/server.py` |
| Spoofed sibling-IdP tokens (🔵 used as 🟣) | Each verifier pins issuer + signing key + audience | `JWTVerifier` in both servers |

---

## Property summary

**Confidentiality** — a note is only readable by its `owner`. The producer
enforces this on the verified `sub` of the 🟣 token; the consumer never learns
the note content if the read fails.

**Integrity** — the `owner` claim is set once at creation, from a
producer-IdP-verified `sub` inside a 🟣 token. No client input can change it.

**Non-repudiation** — the `act.sub` claim in every 🟣 producer token records
which client performed the exchange. The audit trail is embedded in the token
and cannot be forged.

**Least privilege** — each 🔵/🟣 token is bound to exactly one audience by
`aud`. Tokens cannot be repurposed. The exchange client gets a 🟣 token scoped
to the producer only, not to the IdP or to any other service.

**Isolation** — the consumer knows nothing specific about the producer except
the allowlist entry. Discovery is runtime, not compile-time. Adding a new
producer requires no code change, only a config update.

---

## What this demo does NOT protect against

| Gap | Reason it exists | Production mitigation |
|-----|-----------------|----------------------|
| Exchange client authenticated by bare `client_id` | Demo uses public clients | Confidential client with `client_secret`, `private_key_jwt` (RFC 7523), mTLS, or CIMD |
| No token revocation | Demo tokens are short-lived but not revocable | Short-lived tokens + revocation list or introspection (RFC 7662) |
| No rate limiting on the exchange endpoint | Keycloak defaults | IdP config / API gateway |
| Dex password grant | Demo-only convenience | Authorization Code + PKCE; disable ROPC in production |

---

> **Next**: [07 — Running the demo](07-running.md) — code layout, Docker Compose,
> and configuration reference.
