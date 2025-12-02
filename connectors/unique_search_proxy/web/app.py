import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import asyncio
from core import SearchEngineRequestType, get_search_engine, WebSearchResult

# Load environment variables from .env file
load_dotenv()

_LOGGER = logging.getLogger(__name__)


# Pydantic Models


class SearchResponse(BaseModel):
    """Response model for search endpoint."""

    results: List[WebSearchResult] = Field(..., description="Search results")


class ErrorResponse(BaseModel):
    """Response model for errors."""

    status: str = Field(default="failed")
    error: str = Field(..., description="Error message")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _LOGGER.info("Starting Unique Search Proxy...")
    yield
    # Shutdown
    _LOGGER.info("Shutting down Unique Search Proxy...")


app = FastAPI(
    title="Unique Search Proxy",
    description="A unified web search proxy API for multiple search backends",
    version="0.1.0",
    lifespan=lifespan,
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    _LOGGER.exception(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    _LOGGER.exception(f"An error occurred: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=str(exc)).model_dump(),
    )


@app.exception_handler(asyncio.TimeoutError)
async def timeout_exception_handler(request: Request, exc: asyncio.TimeoutError):
    _LOGGER.exception(f"A timeout occurred: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=f"Search engine timed out: {exc}").model_dump(),
    )


@app.post("/search", response_model=SearchResponse)
async def search(request_data: SearchEngineRequestType):
    search_engine = get_search_engine(request_data.search_engine)
    search_engine = search_engine(params=request_data.params)

    async with asyncio.timeout(request_data.timeout):
        results = await search_engine.search(request_data.query)

    return SearchResponse(results=results)


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=2349)
