"""
This module provides a minimal framework for building endpoint classes such that a client can use
the endpoints without having to know the details of the endpoints.
"""

from string import Formatter, Template
from typing import (
    Any,
    Callable,
    Generic,
    Protocol,
    TypeVar,
)

from pydantic import BaseModel

# Type variables
ResponseType = TypeVar("ResponseType", bound=BaseModel)
PathParamsType = TypeVar("PathParamsType", bound=BaseModel)
RequestBodyType = TypeVar("RequestBodyType", bound=BaseModel)

# Helper type to extract constructor parameters

# Type for the constructor of a Pydantic model
ModelConstructor = Callable[..., BaseModel]


# Necessary for typing of make_endpoint_class
class EndpointClassProtocol(
    Protocol,
    Generic[PathParamsType, RequestBodyType, ResponseType],
):
    path_params_model: type[PathParamsType]
    payload_model: type[RequestBodyType]
    response_model: type[ResponseType]

    @staticmethod
    def create_url(*args: Any, **kwargs: Any) -> str: ...

    @staticmethod
    def create_url_from_model(path_params: PathParamsType) -> str: ...

    @staticmethod
    def create_payload(*args: Any, **kwargs: Any) -> dict[str, Any]: ...

    @staticmethod
    def create_payload_from_model(request_body: RequestBodyType) -> dict[str, Any]: ...

    @staticmethod
    def handle_response(response: dict[str, Any]) -> ResponseType: ...

    @staticmethod
    def request_method() -> str: ...


# Model for any client to implement


def build_endpoint_class(
    *,
    method: str,
    url_template: Template,
    path_params_model_type: type[PathParamsType],
    payload_model_type: type[RequestBodyType],
    response_model_type: type[ResponseType],
    dump_options: dict | None = None,
) -> type[EndpointClassProtocol[PathParamsType, RequestBodyType, ResponseType]]:
    """Generate a class with static methods for endpoint handling.

    Uses separate models for path parameters and request body for clean API design.

    Returns a class with static methods:
    - create_url: Creates URL from path parameters
    - create_payload: Creates request body payload
    """
    if not dump_options:
        dump_options = {
            "exclude_unset": True,
            "by_alias": True,
            "exclude_defaults": True,
        }

    class EndpointClass:
        path_params_model = path_params_model_type
        payload_model = payload_model_type
        response_model = response_model_type

        @staticmethod
        def create_url(
            path_params: PathParamsType,
        ) -> str:
            """Create URL from path parameters."""
            path_model = EndpointClass.path_params_model()
            path_dict = path_model.model_dump(**dump_options)

            # Extract expected path parameters from template
            template_params = [
                fname
                for _, fname, _, _ in Formatter().parse(url_template.template)
                if fname is not None
            ]

            # Verify all required path parameters are present
            missing_params = [
                param for param in template_params if param not in path_dict
            ]
            if missing_params:
                raise ValueError(f"Missing path parameters: {missing_params}")

            return url_template.substitute(**path_dict)

        @staticmethod
        def create_url_from_model(path_params: PathParamsType) -> str:
            return url_template.substitute(**path_params.model_dump(**dump_options))

        @staticmethod
        def create_payload(*args: Any, **kwargs: Any) -> dict[str, Any]:
            """Create request body payload."""
            request_model = EndpointClass.payload_model(*args, **kwargs)
            return request_model.model_dump(**dump_options)

        @staticmethod
        def create_payload_from_model(request_body: RequestBodyType) -> dict[str, Any]:
            return request_body.model_dump(**dump_options)

        @staticmethod
        def handle_response(response: dict[str, Any]) -> ResponseType:
            return EndpointClass.response_model.model_validate(response)

        @staticmethod
        def request_method() -> str:
            return method

    return EndpointClass


if __name__ == "__main__":
    # Example models
    class GetUserPathParams(BaseModel):
        """Path parameters for the user endpoint."""

        user_id: int

    class GetUserRequestBody(BaseModel):
        """Request body/query parameters for the user endpoint."""

        include_profile: bool = False

    class UserResponse(BaseModel):
        """Response model for user data."""

        id: int
        name: str

    # Example usage of make_endpoint_class
    UserEndpoint = build_endpoint_class(
        url_template=Template("/users/${user_id}"),
        path_params_model_type=GetUserPathParams,
        payload_model_type=GetUserRequestBody,
        response_model_type=UserResponse,
        method="GET",
    )

    # Create URL from path parameters
    url = UserEndpoint.create_url(user_id=123)
    print(f"URL: {url}")

    # Create payload from request body parameters
    payload = UserEndpoint.create_payload(include_profile=True)
    print(f"Payload: {payload}")

    # Create response from endpoint
    response = UserEndpoint.handle_response(
        {
            "id": 123,
            "name": "John Doe",
        }
    )
    print(f"Response: {response}")
