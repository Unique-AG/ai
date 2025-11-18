from enum import StrEnum
from typing import Any, Callable, Generic, Protocol, TypeVar
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field
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


class RequestContext(BaseModel):
    base_url: str
    headers: dict[str, str] = Field(default_factory=dict)


def _verify_url(url: str) -> None:
    parse_result = urlparse(url)
    if not (parse_result.netloc and parse_result.scheme):
        raise ValueError("Scheme and netloc are required for url")


class EndpointRequestorProtocol(Protocol, Generic[CombinedParamsSpec, ResponseT_co]):
    @classmethod
    def request(
        cls,
        context: RequestContext,
        *args: CombinedParamsSpec.args,
        **kwargs: CombinedParamsSpec.kwargs,
    ) -> ResponseT_co: ...

    @classmethod
    async def request_async(
        cls,
        context: RequestContext,
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
            context: RequestContext,
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

            return cls._operation.handle_response(
                return_value,
                model_validate_options=cls._operation.response_validate_options(),
            )

        @classmethod
        async def request_async(
            cls,
            context: RequestContext,
            headers: dict[str, str] | None = None,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            raise NotImplementedError(
                "Async request not implemented for fake requestor"
            )

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
            context: RequestContext,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            # Create separate instances for path params and payload using endpoint helper
            path_params, payload_model = cls._operation.models_from_combined(
                combined=kwargs
            )

            path = cls._operation.create_path_from_model(
                path_params, model_dump_options=cls._operation.path_dump_options()
            )
            url = urljoin(context.base_url, path)
            _verify_url(url)

            payload = cls._operation.create_payload_from_model(
                payload_model, model_dump_options=cls._operation.payload_dump_options()
            )

            match cls._operation.request_method():
                case HttpMethods.GET:
                    response = requests.get(
                        url, headers=context.headers, params=payload
                    )
                case HttpMethods.POST:
                    response = requests.post(url, headers=context.headers, json=payload)
                case HttpMethods.PUT:
                    response = requests.put(url, headers=context.headers, json=payload)
                case HttpMethods.DELETE:
                    response = requests.delete(
                        url, headers=context.headers, json=payload
                    )
                case HttpMethods.PATCH:
                    response = requests.patch(
                        url, headers=context.headers, json=payload
                    )
                case HttpMethods.OPTIONS:
                    response = requests.options(url, headers=context.headers)
                case HttpMethods.HEAD:
                    response = requests.head(url, headers=context.headers)
                case _:
                    raise ValueError(
                        f"Unsupported HTTP method: {cls._operation.request_method()}"
                    )

            response_json = response.json()

            return cls._operation.handle_response(
                response_json,
                model_validate_options=cls._operation.response_validate_options(),
            )

        @classmethod
        async def request_async(
            cls,
            base_url: str = "",
            headers: dict[str, str] | None = None,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            raise NotImplementedError(
                "Async request not implemented for request requestor"
            )

    return RequestRequestor


def build_httpx_requestor(
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
    import httpx

    class HttpxRequestor(EndpointRequestorProtocol):
        _operation = operation_type

        @classmethod
        def request(
            cls,
            context: RequestContext,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            headers = context.headers or {}

            path_params, payload_model = cls._operation.models_from_combined(
                combined=kwargs
            )

            path = cls._operation.create_path_from_model(
                path_params, model_dump_options=cls._operation.path_dump_options()
            )
            url = urljoin(context.base_url, path)
            _verify_url(url)

            payload = cls._operation.create_payload_from_model(
                payload_model,
                model_dump_options=cls._operation.payload_dump_options(),
            )

            with httpx.Client() as client:
                # For GET requests, send payload as params; for others, send as json
                if cls._operation.request_method() == HttpMethods.GET:
                    response = client.request(
                        method=cls._operation.request_method(),
                        url=url,
                        headers=headers,
                        params=payload,
                    )
                else:
                    response = client.request(
                        method=cls._operation.request_method(),
                        url=url,
                        headers=headers,
                        json=payload,
                    )
                response_json = response.json()
                return cls._operation.handle_response(
                    response_json,
                    model_validate_options=cls._operation.response_validate_options(),
                )

        @classmethod
        async def request_async(
            cls,
            context: RequestContext,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            headers = context.headers or {}

            path_params, payload_model = cls._operation.models_from_combined(
                combined=kwargs
            )

            path = cls._operation.create_path_from_model(
                path_params, model_dump_options=cls._operation.path_dump_options()
            )
            url = urljoin(context.base_url, path)
            _verify_url(url)

            payload = cls._operation.create_payload_from_model(
                payload_model,
                model_dump_options=cls._operation.payload_dump_options(),
            )

            async with httpx.AsyncClient() as client:
                # For GET requests, send payload as params; for others, send as json
                if cls._operation.request_method() == HttpMethods.GET:
                    response = await client.request(
                        method=cls._operation.request_method(),
                        url=url,
                        headers=headers,
                        params=payload,
                    )
                else:
                    response = await client.request(
                        method=cls._operation.request_method(),
                        url=url,
                        headers=headers,
                        json=payload,
                    )
                response_json = response.json()
                return cls._operation.handle_response(
                    response_json,
                    model_validate_options=cls._operation.response_validate_options(),
                )

    return HttpxRequestor


def build_aiohttp_requestor(
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
    import aiohttp

    class AiohttpRequestor(EndpointRequestorProtocol):
        _operation = operation_type

        @classmethod
        def request(
            cls,
            context: RequestContext,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            raise NotImplementedError(
                "Sync request not implemented for aiohttp requestor"
            )

        @classmethod
        async def request_async(
            cls,
            context: RequestContext,
            headers: dict[str, str] | None = None,
            *args: CombinedParamsSpec.args,
            **kwargs: CombinedParamsSpec.kwargs,
        ) -> ResponseType:
            headers = context.headers or {}

            path_params, payload_model = cls._operation.models_from_combined(
                combined=kwargs
            )
            path = cls._operation.create_path_from_model(
                path_params, model_dump_options=cls._operation.path_dump_options()
            )
            url = urljoin(context.base_url, path)
            _verify_url(url)

            async with aiohttp.ClientSession() as session:
                response = await session.request(
                    method=cls._operation.request_method(),
                    url=url,
                    headers=headers,
                    json=cls._operation.create_payload_from_model(
                        payload=payload_model,
                        model_dump_options=cls._operation.payload_dump_options(),
                    ),
                )
                response_json = await response.json()
                return cls._operation.handle_response(
                    response=response_json,
                    model_validate_options=cls._operation.response_validate_options(),
                )

    return AiohttpRequestor


class RequestorType(StrEnum):
    REQUESTS = "requests"
    FAKE = "fake"
    HTTPIX = "httpx"
    AIOHTTP = "aiohttp"


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
) -> type[EndpointRequestorProtocol[CombinedParamsSpec, ResponseType]]:
    match requestor_type:
        case RequestorType.REQUESTS:
            return build_request_requestor(
                operation_type=operation_type, combined_model=combined_model, **kwargs
            )
        case RequestorType.FAKE:
            if return_value is None:
                raise ValueError("return_value is required for fake requestor")
            return build_fake_requestor(
                operation_type=operation_type,
                combined_model=combined_model,
                return_value=return_value,
            )
        case RequestorType.HTTPIX:
            return build_httpx_requestor(
                operation_type=operation_type, combined_model=combined_model
            )
        case RequestorType.AIOHTTP:
            return build_aiohttp_requestor(
                operation_type=operation_type, combined_model=combined_model
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
        path_template=Template("/users/{user_id}"),
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
        context=RequestContext(base_url="https://api.example.com", headers={"a": "b"}),
        user_id=123,
        include_profile=True,
    )

    RequestRequestor = build_request_requestor(
        operation_type=UserEndpoint,
        combined_model=CombinedParams,
    )

    # Check type hints
    response = RequestRequestor().request(
        context=RequestContext(base_url="https://api.example.com", headers={"a": "b"}),
        user_id=123,
        include_profile=True,
    )

    print(response.model_dump())
    print(response.model_json_schema())
    print(response.id)
    print(response.name)
