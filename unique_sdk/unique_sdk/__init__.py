# ruff: noqa: E402
# ruff: noqa: I001
from typing import Literal, Optional

# Unique SDK
# Authors:
# Konstantin Krauss<konstantin@unique.ch>
from unique_sdk._api_version import _ApiVersion

api_key: Optional[str] = None
app_id: Optional[str] = None
api_base: str = "https://gateway.unique.app/public/chat-gen2"
api_version: str = _ApiVersion.CURRENT
api_verify_mode: bool = True
default_http_client: Optional["HTTPClient"] = None

# Set to either 'debug' or 'info', controls console logging
log: Optional[Literal["debug", "info"]] = None

# Webhooks
from unique_sdk._api_requestor import APIRequestor as APIRequestor

# Infrastructure types
from unique_sdk._api_resource import APIResource as APIResource

# Error types
from unique_sdk._error import UniqueError as UniqueError
from unique_sdk._error import APIConnectionError as APIConnectionError
from unique_sdk._error import APIError as APIError
from unique_sdk._error import AuthenticationError as AuthenticationError
from unique_sdk._error import InvalidRequestError as InvalidRequestError
from unique_sdk._error import (
    SignatureVerificationError as SignatureVerificationError,
)
from unique_sdk._error import UniqueErrorWithParamsCode as UniqueErrorWithParamsCode

# HttpClient
from unique_sdk._http_client import (
    HTTPClient as HTTPClient,
)
from unique_sdk._http_client import (
    RequestsClient as RequestsClient,
    HTTPXClient as HTTPXClient,
    AIOHTTPClient as AIOHTTPClient,
)
from unique_sdk._http_client import (
    new_default_http_client as new_default_http_client,
)
from unique_sdk._list_object import ListObject as ListObject
from unique_sdk._request_options import RequestOptions as RequestOptions
from unique_sdk._unique_object import UniqueObject as UniqueObject

# Response types
from unique_sdk._unique_response import UniqueResponse as UniqueResponse
from unique_sdk._unique_response import (
    UniqueResponseBase as UniqueResponseBase,
)

# Util
from unique_sdk._util import (
    convert_to_unique_object as convert_to_unique_object,
)
from unique_sdk._webhook import (
    Webhook as Webhook,
)
from unique_sdk._webhook import (
    WebhookSignature as WebhookSignature,
)
from unique_sdk.api_resources._chat_completion import (
    ChatCompletion as ChatCompletion,
)

# API resources
from unique_sdk.api_resources._event import Event as Event
from unique_sdk.api_resources._message import Message as Message
from unique_sdk.api_resources._integrated import Integrated as Integrated
from unique_sdk.api_resources._search import Search as Search
from unique_sdk.api_resources._content import Content as Content
from unique_sdk.api_resources._search_string import SearchString as SearchString
from unique_sdk.api_resources._short_term_memory import (
    ShortTermMemory as ShortTermMemory,
)
from unique_sdk.api_resources._folder import Folder as Folder
from unique_sdk.api_resources._embedding import Embeddings as Embeddings
from unique_sdk.api_resources._acronyms import Acronyms as Acronyms
from unique_sdk.api_resources._message_assessment import (
    MessageAssessment as MessageAssessment,
)
from unique_sdk.api_resources._space import Space as Space
from unique_sdk.api_resources._agent import Agent as Agent
from unique_sdk.api_resources._mcp import MCP as MCP

# Unique QL
from unique_sdk._unique_ql import UQLOperator as UQLOperator
from unique_sdk._unique_ql import UQLCombinator as UQLCombinator
