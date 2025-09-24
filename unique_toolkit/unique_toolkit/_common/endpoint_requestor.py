from enum import StrEnum
from typing import Any, Callable, Generic, Protocol, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

from unique_toolkit._common.endpoint_builder import (
    ApiOperationProtocol,
    HttpMethods,
    PathParamsSpec,
    PathParamsType,
    PayloadParamSpec,
    PayloadType,
    ResponseType,
)

# Paramspecs
CombinedParamsSpec = ParamSpec("CombinedParamsSpec")

# Type variables
CombinedParamsType = TypeVar("CombinedParamsType", bound=BaseModel)


ResponseT_co = TypeVar("ResponseT_co", bound=BaseModel, covariant=True)


class EndpointRequestorProtocol(Protocol, Generic[CombinedParamsSpec, ResponseT_co]):
    @classmethod
    def request(
        cls,
        headers: dict[str, str],
        *args: CombinedParamsSpec.args,
        **kwargs: CombinedParamsSpec.kwargs,
    ) -> ResponseT_co: ...


def build_fake_requestor(
    operation_type: type[
        ApiOperationProtocol[
            PathParamsSpec,
            PathParamsType,
            PayloadParamSpec,
            PayloadType,
            ResponseType,
        ]
    ],
    combined_model: Callable[CombinedParamsSpec, CombinedParamsType],
    return_value: dict[str, Any],
) -> type[EndpointRequestorProtocol[CombinedParamsSpec, ResponseType]]:
    class FakeRequestor(EndpointRequestorProtocol):
        _operation = operation_type

        @classmethod
        def request(
            cls,
            headers: dict[str, str],
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            try:
                path_params, payload_model = cls._operation.models_from_combined(
                    combined=kwargs
                )
            except Exception as e:
                raise ValueError(
                    f"Invalid parameters passed to combined model {combined_model.__name__}: {e}"
                )

            return cls._operation.handle_response(return_value)

    return FakeRequestor


def build_request_requestor(
    operation_type: type[
        ApiOperationProtocol[
            PathParamsSpec,
            PathParamsType,
            PayloadParamSpec,
            PayloadType,
            ResponseType,
        ]
    ],
    combined_model: Callable[CombinedParamsSpec, CombinedParamsType],
) -> type[EndpointRequestorProtocol[CombinedParamsSpec, ResponseType]]:
    import requests

    class RequestRequestor(EndpointRequestorProtocol):
        _operation = operation_type

        @classmethod
        def request(
            cls,
            headers: dict[str, str],
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            # Create separate instances for path params and payload using endpoint helper
            path_params, payload_model = cls._operation.models_from_combined(
                combined=kwargs
            )

            url = cls._operation.create_url_from_model(path_params)
            payload = cls._operation.create_payload_from_model(payload_model)

            response = requests.request(
                method=cls._operation.request_method(),
                url=url,
                headers=headers,
                json=payload,
            )
            return cls._operation.handle_response(response.json())

    return RequestRequestor


class RequestorType(StrEnum):
    REQUESTS = "requests"
    FAKE = "fake"


def build_requestor(
    requestor_type: RequestorType,
    operation_type: type[
        ApiOperationProtocol[
            PathParamsSpec,
            PathParamsType,
            PayloadParamSpec,
            PayloadType,
            ResponseType,
        ]
    ],
    combined_model: Callable[CombinedParamsSpec, CombinedParamsType],
    return_value: dict[str, Any] | None = None,
    **kwargs: Any,
) -> type[EndpointRequestorProtocol]:
    match requestor_type:
        case RequestorType.REQUESTS:
            return build_request_requestor(
                operation_type=operation_type, combined_model=combined_model
            )
        case RequestorType.FAKE:
            if return_value is None:
                raise ValueError("return_value is required for fake requestor")
            return build_fake_requestor(
                operation_type=operation_type,
                combined_model=combined_model,
                return_value=return_value,
            )


if __name__ == "__main__":
    from string import Template

    from unique_toolkit._common.endpoint_builder import build_api_operation

    class GetUserPathParams(BaseModel):
        user_id: int

    class GetUserRequestBody(BaseModel):
        include_profile: bool = False

    class UserResponse(BaseModel):
        id: int
        name: str

    class CombinedParams(GetUserPathParams, GetUserRequestBody):
        pass

    UserEndpoint = build_api_operation(
        method=HttpMethods.GET,
        url_template=Template("https://api.example.com/users/{user_id}"),
        path_params_constructor=GetUserPathParams,
        payload_constructor=GetUserRequestBody,
        response_model_type=UserResponse,
    )

    FakeUserRequestor = build_fake_requestor(
        operation_type=UserEndpoint,
        combined_model=CombinedParams,
        return_value={"id": 100, "name": "John Doe"},
    )

    # Note that the return value is a pydantic UserResponse object
    response = FakeUserRequestor().request(
        headers={"a": "b"},
        user_id=123,
        include_profile=True,
    )

    RequestRequstor = build_request_requestor(
        operation_type=UserEndpoint,
        combined_model=CombinedParams,
    )

    # Check type hints
    response = RequestRequstor().request(
        headers={"a": "b"}, user_id=123, include_profile=True
    )

    print(response.model_dump())
    print(response.model_json_schema())
    print(response.id)
    print(response.name)
