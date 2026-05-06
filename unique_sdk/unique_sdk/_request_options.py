from typing_extensions import NotRequired, TypedDict


class RequestOptions(TypedDict):
    api_key: NotRequired[str | None]
    api_base: NotRequired[str | None]
    headers: NotRequired[dict[str, str] | None]
