from string import Formatter
from typing import Any, Callable, ParamSpec, Protocol, TypeVar

from pydantic import BaseModel

ResponseType = TypeVar("ResponseType", bound=BaseModel)
RequestType = TypeVar("RequestType", bound=BaseModel)
RequestConstructorSpec = ParamSpec("RequestConstructorSpec")


class Client(Protocol):
    def request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]: ...


def endpoint(
    client: Client,
    url_template: str,
    params: Callable[RequestConstructorSpec, RequestType],
    response_type: type[ResponseType],
) -> Callable[RequestConstructorSpec, ResponseType]:
    def endpoint_f(
        *args: RequestConstructorSpec.args,
        **kwargs: RequestConstructorSpec.kwargs,
    ) -> ResponseType:
        # Create the request model
        request_model = params(*args, **kwargs)
        request_dict = request_model.model_dump(
            exclude_unset=True, by_alias=True, exclude_defaults=True
        )

        # Extract path parameters from the URL template
        path_params = [
            fname
            for _, fname, _, _ in Formatter().parse(url_template)
            if fname is not None
        ]

        # Build URL by replacing path parameters
        url = url_template
        for param in path_params:
            if param in request_dict:
                url = url.replace(f"{{{param}}}", str(request_dict[param]))
                del request_dict[param]  # Remove path param from request body

        return response_type.model_validate(client.request(url, request_dict))

    return endpoint_f
