"""Consumer domain: the archiver MCP server.

The consumer IdP (Dex) runs as a separate container; the consumer server verifies
🔵 tokens against Dex JWKS and never imports producer-specific code.
"""
