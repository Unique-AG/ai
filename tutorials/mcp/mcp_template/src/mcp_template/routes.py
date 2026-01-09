# from pathlib import Path
# from fastapi.responses import FileResponse

from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from starlette.requests import Request

from unique_mcp.provider import BaseProvider


class MCPBaseRoutes(BaseProvider):
    """
    Base routes provider. Extend this class to add custom routes.
    """

    def __init__(self) -> None:
        super().__init__()

    def register(self, *, mcp: FastMCP) -> None:
        """
        Register all custom routes with the MCP server.
        Add your custom routes here using the @mcp.custom_route decorator.
        """

        @mcp.custom_route("/", methods=["GET"])
        async def get_status(request: Request) -> JSONResponse:
            """Health check endpoint"""
            return JSONResponse({"server": "running", "name": "mcp-template"})

        # Uncomment and add favicon.ico to enable favicon route
        # @mcp.custom_route("/favicon.ico", methods=["GET"])
        # async def favicon(request: Request) -> FileResponse:
        #     return FileResponse(path=Path(__file__).parent / "favicon.ico")
