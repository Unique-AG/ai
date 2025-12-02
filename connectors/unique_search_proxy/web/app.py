from flask import Flask, request, jsonify
from pydantic import BaseModel, Field, ValidationError
from typing import List
from dotenv import load_dotenv
from core.schema import WebSearchResult
from core.factory import core_factory, SearchEngineType

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)


# Pydantic Models
class SearchRequest(BaseModel):
    """Request model for search endpoint."""

    search_engine: SearchEngineType = Field(default=SearchEngineType.GOOGLE, description="Search engine to use")
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


# Error Handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e: ValidationError):
    app.logger.exception(f"Validation error: {e}")
    return jsonify(ErrorResponse(error=str(e)).model_dump()), 400


@app.errorhandler(Exception)
def handle_generic_error(e: Exception):
    app.logger.exception(f"An error occurred: {e}")
    return jsonify(ErrorResponse(error=str(e)).model_dump()), 500


@app.route("/search", methods=["POST"])
async def search():
    data = request.get_json()
    request_data = SearchRequest.model_validate(data)
    search_engine_factory, params = core_factory.resolve(request_data.search_engine)
    validated_kwargs = params.model_validate(request_data.kwargs)

    search_engine = search_engine_factory(params=validated_kwargs)
    results = await search_engine.search(request_data.query)

    return jsonify(SearchResponse(results=results).model_dump()), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=2349)