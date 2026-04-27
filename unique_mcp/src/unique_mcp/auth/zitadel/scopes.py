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
