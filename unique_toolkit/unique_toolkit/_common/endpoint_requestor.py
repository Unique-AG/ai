from enum import StrEnum
from typing import Any, Callable, Generic, Protocol, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

from unique_toolkit._common.endpoint_builder import (
    EndpointClassProtocol,
    EndpointMethods,
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


class EndpointRequestorProtocol(Protocol, Generic[CombinedParamsSpec, ResponseType]):
    @classmethod
    def request(
        cls,
        headers: dict[str, str],
        *args: CombinedParamsSpec.args,
        **kwargs: CombinedParamsSpec.kwargs,
    ) -> ResponseType: ...


def build_fake_requestor(
    endpoint_type: type[
        EndpointClassProtocol[
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
        _endpoint = endpoint_type

        @classmethod
        def request(
            cls,
            headers: dict[str, str],
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            try:
                combined_model(*args, **kwargs)
            except Exception as e:
                raise ValueError(
                    f"Invalid parameters passed to combined model {combined_model.__name__}: {e}"
                )

            return cls._endpoint.handle_response(return_value)

    return FakeRequestor


def build_request_requestor(
    endpoint_type: type[
        EndpointClassProtocol[
            PathParamsSpec,
            PathParamsType,
            PayloadParamSpec,
            PayloadType,
            ResponseType,
        ]
    ],
    combined_model: Callable[CombinedParamsSpec, CombinedParamsType],
) -> type[EndpointRequestorProtocol]:
    import requests

    class RequestRequestor(EndpointRequestorProtocol):
        _endpoint = endpoint_type

        @classmethod
        def request(
            cls,
            headers: dict[str, str],
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            url = cls._endpoint.create_url_from_model(combined_model(*args, **kwargs))
            payload = cls._endpoint.create_payload_from_model(
                combined_model(*args, **kwargs)
            )

            response = requests.request(
                method=cls._endpoint.request_method(),
                url=url,
                headers=headers,
                json=payload,
            )
            return cls._endpoint.handle_response(response.json())

    return RequestRequestor


class RequestorType(StrEnum):
    REQUESTS = "requests"
    FAKE = "fake"


def build_requestor(
    requestor_type: RequestorType,
    endpoint_type: type[
        EndpointClassProtocol[
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
                endpoint_type=endpoint_type, combined_model=combined_model
            )
        case RequestorType.FAKE:
            if return_value is None:
                raise ValueError("return_value is required for fake requestor")
            return build_fake_requestor(
                endpoint_type=endpoint_type,
                combined_model=combined_model,
                return_value=return_value,
            )


if __name__ == "__main__":
    from string import Template

    from unique_toolkit._common.endpoint_builder import build_endpoint_class

    class GetUserPathParams(BaseModel):
        user_id: int

    class GetUserRequestBody(BaseModel):
        include_profile: bool = False

    class UserResponse(BaseModel):
        id: int
        name: str

    class CombinedParams(GetUserPathParams, GetUserRequestBody):
        pass

    UserEndpoint = build_endpoint_class(
        method=EndpointMethods.GET,
        url_template=Template("https://api.example.com/users/{user_id}"),
        path_params_constructor=GetUserPathParams,
        payload_constructor=GetUserRequestBody,
        response_model_type=UserResponse,
    )

    FakeUserRequestor = build_fake_requestor(
        endpoint_type=UserEndpoint,
        combined_model=CombinedParams,
        return_value={"id": 100, "name": "John Doe"},
    )

    # Note that the return value is a pydantic UserResponse object
    response = FakeUserRequestor().request(
        headers={"a": "b"},
        user_id=123,
        include_profile=True,
    )

    print(response.model_dump())
    print(response.model_json_schema())
    print(response.id)
    print(response.name)
