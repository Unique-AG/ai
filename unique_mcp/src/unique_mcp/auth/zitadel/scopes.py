"""Default OAuth scopes for Zitadel-backed MCP proxy."""

ZITADEL_DEFAULT_MCP_SCOPES: list[str] = [
    "mcp:tools",
    "mcp:prompts",
    "mcp:resources",
    "mcp:resource-templates",
    "email",
    "openid",
    "profile",
    "urn:zitadel:iam:user:resourceowner",
]

# Scopes sent on the *upstream* Zitadel authorize request only. Zitadel's
# discovery documents openid/profile/email/...; unknown mcp:* scopes plus the
# RFC 8707 ``resource`` parameter have been observed to break the login UI with
# ``Could not find authrequest (CACHE-d24aD)``.
ZITADEL_UPSTREAM_AUTHORIZE_SCOPES: list[str] = [
    "openid",
    "profile",
    "email",
    "offline_access",
    "urn:zitadel:iam:user:resourceowner",
]
