"""
This module provides a minimal framework for building endpoint classes such that a client can use
the endpoints without having to know the details of the endpoints.
"""

from enum import StrEnum
from string import Template
from typing import (
    Any,
    Callable,
    Generic,
    ParamSpec,
    Protocol,
    TypeVar,
    cast,
)

from pydantic import BaseModel
from typing_extensions import deprecated

# Paramspecs
PayloadParamSpec = ParamSpec("PayloadParamSpec")
PathParamsSpec = ParamSpec("PathParamsSpec")

# Type variables
ResponseType = TypeVar("ResponseType", bound=BaseModel, covariant=True)
PathParamsType = TypeVar("PathParamsType", bound=BaseModel)
PayloadType = TypeVar("PayloadType", bound=BaseModel)

# Helper type to extract constructor parameters

# Type for the constructor of a Pydantic model
ModelConstructor = Callable[..., BaseModel]


class HttpMethods(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


# Backward compatibility TODO: Remove in 2.0.0.
EndpointMethods = HttpMethods


class ApiOperationProtocol(
    Protocol,
    Generic[
        PathParamsSpec,
        PathParamsType,
        PayloadParamSpec,
        PayloadType,
        ResponseType,
    ],
):
    @staticmethod
    def path_params_model() -> type[PathParamsType]: ...

    @staticmethod
    def payload_model() -> type[PayloadType]: ...

    @staticmethod
    def response_model() -> type[ResponseType]: ...

    @staticmethod
    def create_path(
        *args: PathParamsSpec.args, **kwargs: PathParamsSpec.kwargs
    ) -> str: ...

    @staticmethod
    def create_path_from_model(path_params: PathParamsType) -> str: ...

    @deprecated(
        "Use create_path instead to create a path and then combine with base url to create a full url."
    )
    @staticmethod
    def create_url(
        *args: PathParamsSpec.args, **kwargs: PathParamsSpec.kwargs
    ) -> str: ...

    @deprecated(
        "Use create_path instead to create a path and then combine with base url to create a full url."
    )
    @staticmethod
    def create_url_from_model(path_params: PathParamsType) -> str: ...

    @staticmethod
    def create_payload(
        *args: PayloadParamSpec.args, **kwargs: PayloadParamSpec.kwargs
    ) -> dict[str, Any]: ...

    @staticmethod
    def create_payload_from_model(payload: PayloadType) -> dict[str, Any]: ...

    @staticmethod
    def handle_response(response: dict[str, Any]) -> ResponseType: ...

    @staticmethod
    def request_method() -> EndpointMethods: ...

    @staticmethod
    def models_from_combined(
        combined: dict[str, Any],
    ) -> tuple[PathParamsType, PayloadType]: ...


# Model for any client to implement
def build_api_operation(
    *,
    method: HttpMethods,
    path_template: Template,
    path_params_constructor: Callable[PathParamsSpec, PathParamsType],
    payload_constructor: Callable[PayloadParamSpec, PayloadType],
    response_model_type: type[ResponseType],
    dump_options: dict | None = None,
) -> type[
    ApiOperationProtocol[
        PathParamsSpec,
        PathParamsType,
        PayloadParamSpec,
        PayloadType,
        ResponseType,
    ]
]:
    """Generate a class with static methods for endpoint handling.

    Uses separate models for path parameters and request body for clean API design.

    Returns a class with static methods:
    - create_url: Creates URL from path parameters
    - create_payload: Creates request body payload
    """

    # Verify that the path_params_constructor and payload_constructor are valid pydantic models
    if not dump_options:
        dump_options = {
            "exclude_unset": True,
            "by_alias": True,
            "exclude_defaults": True,
        }

    class Operation(ApiOperationProtocol):
        @staticmethod
        def path_params_model() -> type[PathParamsType]:
            return cast(type[PathParamsType], path_params_constructor)

        @staticmethod
        def payload_model() -> type[PayloadType]:
            return cast(type[PayloadType], payload_constructor)

        @staticmethod
        def response_model() -> type[ResponseType]:
            return response_model_type

        @staticmethod
        def path_template() -> Template:
            return path_template

        @staticmethod
        def create_path_from_model(path_params: PathParamsType) -> str:
            return path_template.substitute(**path_params.model_dump(**dump_options))

        @staticmethod
        def create_path(
            *args: PathParamsSpec.args, **kwargs: PathParamsSpec.kwargs
        ) -> str:
            model = Operation.path_params_model()(*args, **kwargs)
            return Operation.create_path_from_model(model)

        @staticmethod
        def create_payload(
            *args: PayloadParamSpec.args, **kwargs: PayloadParamSpec.kwargs
        ) -> dict[str, Any]:
            """Create request body payload."""
            request_model = Operation.payload_model()(*args, **kwargs)
            return request_model.model_dump(**dump_options)

        @staticmethod
        def create_payload_from_model(payload: PayloadType) -> dict[str, Any]:
            return payload.model_dump(**dump_options)

        @staticmethod
        def handle_response(response: dict[str, Any]) -> ResponseType:
            return Operation.response_model().model_validate(response)

        @staticmethod
        def request_method() -> HttpMethods:
            return method

        @staticmethod
        def models_from_combined(
            combined: dict[str, Any],
        ) -> tuple[PathParamsType, PayloadType]:
            path_params = Operation.path_params_model().model_validate(
                combined, by_alias=True, by_name=True
            )
            payload = Operation.payload_model().model_validate(
                combined, by_alias=True, by_name=True
            )
            return path_params, payload

    return Operation
