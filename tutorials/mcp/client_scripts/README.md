# MCP Client Debug Scripts

This folder contains standalone scripts for manually debugging MCP client behavior.

## Debug MCP Auth

Use `debug_mcp_auth.py` to inspect OAuth discovery, MCP endpoint behavior, and the tools returned by a remote MCP server. The script first performs read-only HTTP probes, then uses FastMCP's client to complete the configured auth flow and call `list_tools()`.

Run it from the repository root with `uv`:

```bash
uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py https://example.com/my-server/
```

You can also pass the final MCP endpoint explicitly:

```bash
uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py --server-url https://example.com/my-server/mcp
```

Or provide the server URL through an environment variable:

```bash
DEBUG_MCP_AUTH_SERVER_URL=https://example.com/my-server/ \
  uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py
```

If the server URL is a prefix, the script appends `mcp` by default. Override that with `--mcp-path`:

```bash
uv run --with fastmcp --with httpx tutorials/mcp/client_scripts/debug_mcp_auth.py \
  --server-url https://example.com/my-server/ \
  --mcp-path custom-mcp-path
```

## Useful Options

- `--auth oauth`: Use FastMCP OAuth for the final connection. This is the default.
- `--auth none`: Connect without FastMCP auth after the discovery probes.
- `--protocol-version`: Set the MCP protocol version used in the unauthenticated initialize probe.
- `--client-name` and `--client-version`: Set the `clientInfo` values used in the initialize probe.
- `--timeout`: Set the HTTP timeout, in seconds, for metadata probes.
- `--body-preview-chars`: Limit how many characters are printed from each request or response body.
- `--debug-logs`: Enable debug logging for FastMCP and httpx internals.

## What The Output Shows

The script prints numbered sections so you can compare the server's advertised metadata with what the FastMCP client does.

### 0. Configuration

Shows the input server URL, the normalized MCP endpoint, protocol version, client info, and body preview size. Use this section to confirm the script is probing the endpoint you intended.

### 1. Probe MCP Endpoint Without Authorization

Sends an unauthenticated JSON-RPC `initialize` request to the MCP endpoint. This helps verify:

- Whether the endpoint is reachable.
- Which HTTP status code is returned before authentication.
- Whether the response includes a `WWW-Authenticate` header.
- Whether that header advertises an OAuth protected-resource metadata URL.

### 2. Inspect Protected-Resource Metadata Candidates

Fetches the advertised protected-resource metadata URL, plus common fallback locations under `/.well-known/oauth-protected-resource`. Successful JSON responses show fields such as `authorization_servers`, which tell the client where to discover OAuth server metadata.

### 3. Inspect Authorization-Server Metadata Candidates

Fetches OAuth or OpenID metadata from discovered authorization servers and common fallback locations. This section is useful for checking whether endpoints such as authorization, token, registration, and issuer metadata are present and consistent.

### 4. Connect With FastMCP OAuth Client And List Tools

Runs the FastMCP client against the normalized MCP endpoint. With OAuth enabled, FastMCP may open a browser or print a login URL. Complete that flow when prompted, then the script continues and calls `list_tools()`.

This section also traces HTTP exchanges that FastMCP performs during auth. Sensitive headers and common token fields are redacted before printing.

### 5. Tools

Prints the tools returned by the server, including each tool name, description, and input schema when available. If no tools are returned, the script prints `No tools returned.`

## Redaction

The script redacts sensitive headers such as `Authorization`, `Cookie`, and `Set-Cookie`. It also redacts common OAuth body fields such as `access_token`, `refresh_token`, `id_token`, `client_secret`, and `code` in JSON or form-encoded bodies.

Review output before sharing it externally, especially when server-specific metadata or URLs are sensitive.
