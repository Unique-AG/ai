from typing import Any, Callable, Protocol, TypeVar

from pydantic import BaseModel

ResponseType = TypeVar("ResponseType", bound=BaseModel)
RequestType = TypeVar("RequestType", bound=BaseModel)


class Client(Protocol):
    def request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]: ...


def endpoint(
    params: type[RequestType],
    response_type: type[ResponseType],
) -> Callable[[Client, RequestType], ResponseType]:
    """
    Creates a typed API endpoint function.

    Args:
        params: Pydantic model class for request parameters
        response_type: Pydantic model class for response

    Returns:
        A function that takes (client, params_instance) and returns response
    """

    def endpoint_f(
        client: Client,
        params_instance: RequestType,
    ) -> ResponseType:
        # Convert the request model to dict
        request_dict = params_instance.model_dump(
            exclude_unset=True, by_alias=True, exclude_defaults=True
        )

        # For now, assuming endpoint is extracted from somewhere or passed differently
        # This is a simplified version - you may need to adapt based on your actual use case
        return response_type.model_validate(client.request("", request_dict))

    return endpoint_f
