import contextlib
import importlib
import logging

import uvicorn
import yaml
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

logging.basicConfig(level=logging.INFO, format="%(levelname)s:  %(message)s")
logger = logging.getLogger(__name__)

CONFIG_FILE = "mcp-modules.yaml"
HOST = "0.0.0.0"
PORT = 5032

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]


def load_module_list(config_file: str) -> list[str]:
    with open(config_file) as f:
        modules = yaml.safe_load(f)
    return modules or []


def register_mcp_servers(
    modules: list[str],
) -> tuple[list[Mount], list]:
    """Import each module's `mcp` instance and collect Starlette mounts + lifespans."""
    mounts: list[Mount] = []
    lifespans = []

    for mod_name in modules:
        try:
            module = importlib.import_module(f"mcp_server_multiplexer.{mod_name}.app")
            mcp_server = getattr(module, "mcp")
            starlette_app = mcp_server.http_app()

            mounts.append(Mount(f"/{mod_name}", app=starlette_app))
            lifespans.append(starlette_app.router.lifespan_context)

            logger.info(f"Mounted MCP server: /{mod_name}/mcp")
        except Exception:
            logger.error(
                f"Failed to load MCP module '{mod_name}', skipping.",
                exc_info=True,
            )

    return mounts, lifespans


def combine_lifespans(*lifespans):
    """Merge multiple ASGI lifespan contexts into one."""

    @contextlib.asynccontextmanager
    async def combined(app):
        async with contextlib.AsyncExitStack() as stack:
            for ls in lifespans:
                await stack.enter_async_context(ls(app))
            yield

    return combined


async def health(_request):
    return JSONResponse({"status": "ok"})


def create_app(config_file: str = CONFIG_FILE) -> Starlette:
    modules = load_module_list(config_file)
    mounts, lifespans = register_mcp_servers(modules)

    routes = [Route("/health", health)] + mounts

    app = Starlette(
        routes=routes,
        middleware=custom_middleware,
        lifespan=combine_lifespans(*lifespans) if lifespans else None,
    )

    logger.info("=" * 50)
    logger.info("MCP Service started")
    logger.info(f"  Health:  http://{HOST}:{PORT}/health")
    for mount in mounts:
        logger.info(f"  MCP:     http://{HOST}:{PORT}{mount.path}/mcp")
    logger.info("=" * 50)

    return app


app = create_app()


def main():
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
