# Per-request identity

Every Unique API call needs `user_id` + `company_id` for **this** request. Do not hard-code a tenant in env on a multi-user server.

The MCP server is an OAuth proxy: the client holds a short-lived FastMCP JWT; the server swaps it for the stored Zitadel token. Prefer JWT claims that embed `sub` and `urn:zitadel:iam:user:resourceowner:id` (Zitadel JWT token type + resourceowner scope).

## Resolver

Use **`await get_unique_settings_async()`** in the tool body.

| Order | Source | When it wins |
| ----- | ------ | ------------ |
| 1 | Zitadel JWT claims | `sub` + resourceowner company id after token swap |
| 2 | Zitadel `/userinfo` | Async only; JWT incomplete |
| 3 | `_meta` `unique.app/auth/user-id` + `company-id` | **No access token** (trusted internal callers) |
| 4 | Env `UNIQUE_AUTH_*` | No token and no `_meta` auth |

Both IDs must be present for a source to win. If a token is present but JWT and userinfo cannot yield both IDs, **raise** — never fall through to the env service user.

Sync `get_unique_settings()` skips `/userinfo` and can silently use `UNIQUE_AUTH_*` on incomplete JWTs. Deprecated for new tools.

Chat (`unique.app/chat/chat-id` and companions) is applied whenever `chat-id` is present, independent of auth ranking. Missing companion fields become the sentinel `mcp-unknown`.

## Security

`_meta` identity is caller-supplied and **not bound to the bearer token**. Honouring it while authenticated would let any client assert another tenant. `unique-mcp` therefore ignores `_meta` auth as soon as `Authorization` is set. Do not reimplement a lookup that ranks `_meta` above the token.

Use `_meta` auth only from callers you fully trust, with no `Authorization` header. Unique AI normally authenticates; identity then comes from JWT/userinfo, while `_meta` still carries chat + config.

Do not set `UNIQUE_AUTH_USER_ID` / `UNIQUE_AUTH_COMPANY_ID` on deployed apps.

## OAuth wiring

- `create_zitadel_oidc_proxy` (discovery) or `create_zitadel_oauth_proxy` (explicit endpoints).
- Required `client_storage`: `MemoryStore()` locally; shared encrypted store in prod (not FastMCP's per-pod disk default).
- Scopes advertised: `openid`, `profile`, `email`, `urn:zitadel:iam:user:resourceowner`, `mcp:tools`, `mcp:prompts`, `mcp:resources`, `mcp:resource-templates`.
- Zitadel app: JWT token type, include user info in ID token, redirect `{public}/auth/callback`.

Env: `ZITADEL_BASE_URL`, `ZITADEL_CLIENT_ID`, `ZITADEL_CLIENT_SECRET`; `UNIQUE_MCP_PUBLIC_BASE_URL` / `UNIQUE_MCP_LOCAL_BASE_URL`. Toolkit API creds (`UNIQUE_APP_*`, `UNIQUE_API_BASE_URL`) still required.
