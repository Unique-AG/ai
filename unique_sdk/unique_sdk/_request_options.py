from typing import Dict, Optional

from typing_extensions import NotRequired, TypedDict


class RequestOptions(TypedDict):
    api_key: NotRequired[Optional[str]]
    api_base: NotRequired[Optional[str]]
    headers: NotRequired[Optional[Dict[str, str]]]
