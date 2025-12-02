import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv

from core.schema import WebSearchResult, SearchEngineType
from core.factory import core_factory

# Load environment variables from .env file
load_dotenv()

_LOGGER = logging.getLogger(__name__)


# Pydantic Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    search_engine: SearchEngineType = Field(
        default=SearchEngineType.GOOGLE, description="Search engine to use"
    )
    query: str = Field(..., min_length=1, description="Search query string")
    kwargs: dict = Field(
        default_factory=dict,
        description="Additional keyword arguments for the search engine",
    )


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


@app.post("/search", response_model=SearchResponse)
async def search(request_data: SearchRequest):
    search_engine_factory, params = core_factory.resolve(request_data.search_engine)
    validated_kwargs = params.model_validate(request_data.kwargs)

    search_engine = search_engine_factory(params=validated_kwargs)
    results = await search_engine.search(request_data.query)

    return SearchResponse(results=results)


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=2349)
