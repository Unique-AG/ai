"""
This module provides a minimal framework for building endpoint classes such that a client can use
the endpoints without having to know the details of the endpoints.
"""

from collections.abc import Callable
from string import Formatter, Template
from typing import (
    Any,
    Generic,
    ParamSpec,
    Protocol,
    TypeVar,
)

from pydantic import BaseModel

# Type variables
ResponseType = TypeVar("ResponseType", bound=BaseModel)
PathParamsType = TypeVar("PathParamsType", bound=BaseModel)
RequestBodyType = TypeVar("RequestBodyType", bound=BaseModel)

# ParamSpecs for function signatures
RequestConstructorSpec = ParamSpec("RequestConstructorSpec")
PathParamsSpec = ParamSpec("PathParamsSpec")
RequestBodySpec = ParamSpec("RequestBodySpec")


# Necessary for typing of make_endpoint_class
class EndpointClassProtocol(Protocol, Generic[PathParamsSpec, RequestBodySpec]):
    @staticmethod
    def create_url(
        *args: PathParamsSpec.args, **kwargs: PathParamsSpec.kwargs
    ) -> str: ...

    @staticmethod
    def create_payload(
        *args: RequestBodySpec.args, **kwargs: RequestBodySpec.kwargs
    ) -> dict[str, Any]: ...


# Model for any client to implement
class Client(Protocol):
    def request(
        self,
        endpoint: EndpointClassProtocol,
    ) -> dict[str, Any]: ...


def build_endpoint_class(
    *,
    url_template: Template,
    path_params_model: Callable[PathParamsSpec, PathParamsType],
    payload_model: Callable[RequestBodySpec, RequestBodyType],
    response_model: type[ResponseType],
    dump_options: dict | None = None,
) -> type[EndpointClassProtocol[PathParamsSpec, RequestBodySpec]]:
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

    class EndpointClass(EndpointClassProtocol):
        @staticmethod
        def create_url(
            *args: PathParamsSpec.args, **kwargs: PathParamsSpec.kwargs
        ) -> str:
            """Create URL from path parameters."""
            path_model = path_params_model(*args, **kwargs)
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
        def create_payload(
            *args: RequestBodySpec.args, **kwargs: RequestBodySpec.kwargs
        ) -> dict[str, Any]:
            """Create request body payload."""
            request_model = payload_model(*args, **kwargs)
            return request_model.model_dump(**dump_options)

        @staticmethod
        def handle_response(response: dict[str, Any]) -> ResponseType:
            return response_model.model_validate(response)

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
        path_params_model=GetUserPathParams,
        payload_model=GetUserRequestBody,
        response_model=UserResponse,
    )

    # Create URL from path parameters
    url = UserEndpoint.create_url(user_id=123)
    print(f"URL: {url}")

    # Create payload from request body parameters
    payload = UserEndpoint.create_payload(include_profile=True)
    print(f"Payload: {payload}")
