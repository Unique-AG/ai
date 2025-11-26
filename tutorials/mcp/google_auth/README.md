# Google Auth MCP Tutorial

This tutorial demonstrates building an HTTP-streamable MCP server with FastMCP, with a focus on demonstrating how to authenticate with Google OAuth.

Visit: [https://unique-ag.github.io/](https://unique-ag.github.io/ai/Tutorials/mcp_google_auth/) for the documentation.

## Setup

1. Install dependencies using uv:
   ```bash
   uv sync
   ```

2. Create a `.env` file with your Google OAuth credentials:
   ```
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ```

3. Run the server:
   ```bash
   uv run python -m google_auth.google_auth_server
   ```

## Google OAuth Setup

To use this example, you need to:

1. **Create a Google OAuth Client:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google+ API
   - Go to "Credentials" and create an OAuth 2.0 Client ID
   - Set authorized redirect URIs to match your `BASE_URL` (e.g., `http://localhost:8003/auth/callback`)

2. **Configure Environment Variables:**
   - Set `GOOGLE_CLIENT_ID` to your Google OAuth Client ID
   - Set `GOOGLE_CLIENT_SECRET` to your Google OAuth Client Secret

3. **Required Scopes:**
   - `openid`: Required for OpenID Connect authentication
   - `https://www.googleapis.com/auth/userinfo.email`: Required to access user email information

