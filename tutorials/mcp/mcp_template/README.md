# MCP Template

A clean template for creating MCP (Model Context Protocol) servers following best practices.

## Structure

- `src/mcp_template/mcp_template_server.py` - Main server entry point
- `src/mcp_template/tools.py` - Tool providers extending BaseProvider
- `src/mcp_template/routes.py` - Custom routes extending BaseProvider
- `src/mcp_template/util.py` - Utility functions for auth and user management
- `src/mcp_template/mcp_client.py` - Example client code

## Setup

1. Copy `unique.env.example` to `unique.env` and fill in your values
2. Copy `zitadel.env.example` to `zitadel.env` and fill in your values
3. Install dependencies: `uv sync`
4. Run the server: `uv run mcp-template`

## Documentation

Visit: [https://unique-ag.github.io/](https://unique-ag.github.io/ai/Tutorials/mcp_template/) for the documentation.

