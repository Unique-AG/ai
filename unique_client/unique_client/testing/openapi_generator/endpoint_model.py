"""
Type-safe Pydantic models for API endpoints.
"""

from typing import Any, Dict, Generic, Type, TypedDict, TypeVar

from pydantic import BaseModel, ValidationError


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


# Generic type variables for type safety
RequestModelT = TypeVar("RequestModelT", bound=BaseModel)
ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)
PathParamsT = TypeVar("PathParamsT")  # Can be TypedDict or dict[str, str]


class BaseEndpoint(BaseModel, Generic[RequestModelT, ResponseModelT, PathParamsT]):
    """
    Base class for type-safe API endpoints.

    Provides:
    - Type-safe request building
    - Response validation and parsing
    - Type-safe URL building with typed path parameters
    - Parameter validation
    """

    path: str
    method: str
    operation_id: str

    # Model classes will be set by subclasses
    request_model: Type[RequestModelT]
    response_model: Type[ResponseModelT]
    path_param_names: list[str] = []

    class Config:
        frozen = True  # Make endpoint immutable
        arbitrary_types_allowed = True  # Allow Type[] fields

    def build_request(self, **params: Any) -> RequestModelT:
        """Build a type-safe request from parameters."""
        if self.path_param_names:
            # Exclude path parameters from request body
            request_data = {
                k: v for k, v in params.items() if k not in self.path_param_names
            }
        else:
            request_data = params

        return self.request_model(**request_data)

    def parse_response(self, response_data: Dict[str, Any]) -> ResponseModelT:
        """Parse and validate response data into the success model."""
        try:
            return self.response_model.model_validate(response_data)
        except ValidationError as e:
            raise ValueError(
                f"Failed to parse response for {self.operation_id}: {e}"
            ) from e

    def build_url_with_params(self, **path_params: dict[str, str]) -> str:
        """Build URL with typed path parameters."""
        return self.build_url(**path_params)

    def build_url(self, **path_params: Any) -> str:
        """Build the full URL with path parameters."""
        url = self.path
        for key, value in path_params.items():
            # Convert all path parameters to strings for URL construction
            url = url.replace(f"{{{key}}}", str(value))
        return url

    def get_method(self) -> str:
        """Get the HTTP method for this endpoint."""
        return self.method.upper()

    def to_api_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parameters to API format with camelCase field names."""
        api_result = {}
        for key, value in params.items():
            # Convert snake_case keys to camelCase for API
            api_key = snake_to_camel(key)
            api_result[api_key] = value

        return api_result


# Helper types for endpoints without path parameters
class NoPathParams(TypedDict):
    """Empty TypedDict for endpoints without path parameters."""

    pass
