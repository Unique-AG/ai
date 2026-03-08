from pathlib import Path

from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from starlette.requests import Request

from unique_mcp.provider import BaseProvider


class MCPBaseRoutes(BaseProvider):
    def __init__(self) -> None:
        super().__init__()

    def register(self, *, mcp: FastMCP) -> None:
        @mcp.custom_route("/", methods=["GET"])
        async def get_status(request: Request) -> JSONResponse:
            return JSONResponse({"server": "running"})

        @mcp.custom_route("/favicon.ico", methods=["GET"])
        async def favicon(request: Request) -> FileResponse:
            return FileResponse(path=Path(__file__).parent / "favicon.ico")

        @mcp.custom_route("/health", methods=["GET"])
        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "healthy"})
