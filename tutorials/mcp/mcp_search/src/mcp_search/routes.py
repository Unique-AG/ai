from pathlib import Path

from fastapi.responses import FileResponse, JSONResponse
from fastmcp import FastMCP
from starlette.requests import Request

_CUSTOM_ROUTES_PROVIDER = FastMCP()


@_CUSTOM_ROUTES_PROVIDER.custom_route("/", methods=["GET"])
async def get_status(request: Request) -> JSONResponse:
    return JSONResponse({"server": "running"})


@_CUSTOM_ROUTES_PROVIDER.custom_route("/favicon.ico", methods=["GET"])
async def favicon(request: Request) -> FileResponse:
    return FileResponse(path=Path(__file__).parent / "favicon.ico")


@_CUSTOM_ROUTES_PROVIDER.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})


def get_custom_routes_provider() -> FastMCP:
    return _CUSTOM_ROUTES_PROVIDER
