from typing import Any, Callable, Generic, Protocol, TypeVar

from pydantic import BaseModel
from typing_extensions import ParamSpec

from unique_toolkit._common.endpoint_builder import EndpointClassProtocol

PathParamsSpec = ParamSpec("PathParamsSpec")
RequestBodySpec = ParamSpec("RequestBodySpec")
CombinedParamsSpec = ParamSpec("CombinedParamsSpec")


PathParamsType = TypeVar("PathParamsType", bound=BaseModel)
RequestBodyType = TypeVar("RequestBodyType", bound=BaseModel)
ResponseType = TypeVar("ResponseType", bound=BaseModel, covariant=True)
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
            RequestBodySpec,
            PathParamsType,
            RequestBodyType,
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
            return cls._endpoint.handle_response(return_value)

    return FakeRequestor


def build_request_requestor(
    endpoint_type: type[
        EndpointClassProtocol[
            PathParamsSpec,
            RequestBodySpec,
            PathParamsType,
            RequestBodyType,
            ResponseType,
        ]
    ],
    combined_model: Callable[CombinedParamsSpec, CombinedParamsType],
    return_value: dict[str, Any],
) -> type[EndpointRequestorProtocol[CombinedParamsSpec, ResponseType]]:
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
            path_params = cls._endpoint.path_params_model(*args, **kwargs)
            url = cls._endpoint.create_url_from_model(path_params)

            payload_model = cls._endpoint.payload_model(*args, **kwargs)
            payload = cls._endpoint.create_payload_from_model(payload_model)

            response = requests.request(
                method=cls._endpoint.request_method(),
                url=url,
                headers=headers,
                json=payload,
            )
            return cls._endpoint.handle_response(response.json())

    return RequestRequestor


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
        method="GET",
        url_template=Template("https://api.example.com/users/{user_id}"),
        path_params_model_type=GetUserPathParams,
        payload_model_type=GetUserRequestBody,
        response_model_type=UserResponse,
    )

    FakeUserRequestor = build_fake_requestor(
        endpoint_type=UserEndpoint,
        combined_model=CombinedParams,
        return_value={"id": 100, "name": "Cedric"},
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
