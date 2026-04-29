import base64
import binascii
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any

import requests
from dotenv import load_dotenv
from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from pydantic import Field
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

# Ensure the static directory exists and contains favicon.ico
FAVICON_PATH = Path(__file__).parent / "favicon.ico"


# Load environment variables from .env file
load_dotenv()

user_id = os.getenv("USER_ID", "default_user_id")
company_id = os.getenv("COMPANY_ID", "default_company_id")
ZITADEL_URL = os.getenv("ZITADEL_URL", "http://localhost:10116")


upstream_client_id = os.getenv("UPSTREAM_CLIENT_ID", "default_client_id")
upstream_client_secret = os.getenv("UPSTREAM_CLIENT_SECRET", "default_client_secret")

base_url_env = os.getenv("BASE_URL_ENV", "https://default.ngrok-free.app")


base_url_arg = sys.argv[1] if len(sys.argv) > 1 else base_url_env

print("base_url_arg", base_url_arg)


token_verifier = JWTVerifier(
    jwks_uri=f"{ZITADEL_URL}/oauth/v2/keys",
    issuer=f"{ZITADEL_URL}",
    algorithm=None,
    audience=None,
    # required_scopes=[],
)

auth = OAuthProxy(
    upstream_authorization_endpoint=f"{ZITADEL_URL}/oauth/v2/authorize",
    upstream_token_endpoint=f"{ZITADEL_URL}/oauth/v2/token",
    upstream_client_id=upstream_client_id,
    upstream_client_secret=upstream_client_secret,
    upstream_revocation_endpoint=f"{ZITADEL_URL}/oauth/v2/revoke",
    token_verifier=token_verifier,
    base_url=base_url_arg,
    redirect_path=None,
    issuer_url=None,
    service_documentation_url=None,
    allowed_client_redirect_uris=None,
    valid_scopes=[
        "mcp:tools",
        "mcp:prompts",
        "mcp:resources",
        "mcp:resource-templates",
        "email",
        "openid",
        "profile",
        "urn:zitadel:iam:user:resourceowner",
    ],
    forward_pkce=True,
    token_endpoint_auth_method="client_secret_post",
    extra_authorize_params=None,
    extra_token_params=None,
)


def _decode_jwt_segment(segment: str) -> dict[str, Any] | None:
    """Decode a single base64url JWT segment to a JSON object, if it parses."""
    try:
        padding = "=" * (-len(segment) % 4)
        raw = base64.urlsafe_b64decode(segment + padding)
    except (ValueError, binascii.Error):
        return None
    try:
        decoded = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _format_jwt(token: str) -> str:
    """Render a one-line summary of a JWT (header alg + key claims) for logs."""
    parts = token.split(".")
    if len(parts) != 3:
        return f"<opaque, {len(token)} chars>"
    header = _decode_jwt_segment(parts[0]) or {}
    claims = _decode_jwt_segment(parts[1]) or {}
    interesting = {k: claims.get(k) for k in ("iss", "aud", "client_id", "sub", "scope", "exp", "iat", "jti") if k in claims}
    return f"alg={header.get('alg')!r} claims={json.dumps(interesting, sort_keys=True)}"


class BearerTokenLoggingMiddleware:
    """ASGI middleware that prints the incoming Authorization header and JSON-RPC method
    *before* any FastMCP auth or validation runs. Drop-in safe: buffers and replays the
    request body so downstream handlers see the original stream, and forwards any
    subsequent ASGI events (e.g. http.disconnect) to the wrapped app.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        auth_value: str | None = None
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                auth_value = value.decode("latin-1", errors="replace")
                break

        print(f"\n[mcp-demo] >>> {method} {path}")
        if auth_value is None:
            print("[mcp-demo]     Authorization: <none>")
        elif auth_value.lower().startswith("bearer "):
            token = auth_value[len("bearer "):].strip()
            print(f"[mcp-demo]     Authorization: Bearer ({len(token)} chars)")
            print(f"[mcp-demo]     token: {_format_jwt(token)}")
            parts = token.split(".")
            if len(parts) == 3:
                claims = _decode_jwt_segment(parts[1])
                if claims is not None:
                    print(f"[mcp-demo]     token claims (full): {json.dumps(claims, indent=2, sort_keys=True)}")
        else:
            print(f"[mcp-demo]     Authorization: {auth_value[:60]}{'…' if len(auth_value) > 60 else ''}")

        if method != "POST":
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "http.request":
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            else:
                async def passthrough_receive(_first: dict[str, Any] = message) -> dict[str, Any]:
                    if not getattr(passthrough_receive, "_consumed", False):
                        passthrough_receive._consumed = True  # type: ignore[attr-defined]
                        return _first
                    return await receive()

                await self.app(scope, passthrough_receive, send)
                return

        full_body = b"".join(chunks)
        try:
            payload = json.loads(full_body.decode("utf-8", errors="replace"))
        except (ValueError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            rpc_method = payload.get("method")
            rpc_id = payload.get("id")
            if rpc_method:
                print(f"[mcp-demo]     jsonrpc id={rpc_id!r} method={rpc_method!r}")

        replayed = False

        async def replay_receive() -> dict[str, Any]:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": full_body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)


custom_middleware = [
    Middleware(BearerTokenLoggingMiddleware),
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

# mcp = FastMCP.from_fastapi(app=app,auth=auth,debug=True,log_level="debug")
mcp = FastMCP("Demo 🚀", auth=auth)


def get_user():
    token = get_access_token()
    if token is not None:
        print("token", token)
        headers = {
            "Authorization": f"Bearer {token.token}",
        }
        response = requests.get(f"{ZITADEL_URL}/oidc/v1/userinfo", headers=headers)
    return response.json()


@mcp.tool(
    name="addition",  # Custom tool name for the LLM
    title="addition",  # Custom display name
    description="This tool does add two numbers",  # Custom description
    meta={
        "unique.app/icon": "calculator",
        "unique.app/system-prompt": "Choose this tool if you need to add two numbers together",
    },
)
def add(
    a: Annotated[int, Field(description="First number to add", default=0)],
    b: Annotated[int, Field(description="Second number to add", default=0)],
) -> int:
    """Add two numbers"""

    return a + b


@mcp.tool
def identify(user_prompt: str) -> str:
    """Identify the user"""
    user = get_user()
    data = json.dumps(user)
    print(data)
    return data


@mcp.custom_route("/", methods=["GET"])
async def get_status(request: Request):
    return JSONResponse({"server": "running"})


@mcp.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request):
    return FileResponse(FAVICON_PATH)


def main() -> None:
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8003,
        debug=True,
        log_level="debug",
        middleware=custom_middleware,
    )


if __name__ == "__main__":
    main()
