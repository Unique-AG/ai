"""OAuth discovery metadata fix — advertise ``client_secret_post`` only.

FastMCP's token endpoint (as of 3.4.4) only parses client credentials from the
request body, yet its discovery metadata also advertises ``client_secret_basic``.
The MCP TypeScript SDK prefers ``client_secret_basic`` when advertised, so token
exchanges from Unique's platform fail with 401 "Missing client_id". Dropping
basic from the advertised methods steers the SDK to ``client_secret_post``,
which works. Inert while the server runs without OAuth (no /.well-known routes).
"""

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class AdvertisePostAuthOnly(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/.well-known/"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        try:
            data = json.loads(body)
            for key in (
                "token_endpoint_auth_methods_supported",
                "revocation_endpoint_auth_methods_supported",
            ):
                if isinstance(data.get(key), list) and "client_secret_post" in data[key]:
                    data[key] = ["client_secret_post"]
            body = json.dumps(data).encode()
        except (ValueError, TypeError):
            pass
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
