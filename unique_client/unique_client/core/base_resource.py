"""
Base class for API resources using Pydantic models.

This provides the foundation for all API resource classes in the v2 SDK.
All API methods must use Pydantic models for both input parameters and response parsing.
"""

from typing import ClassVar, Optional, Type, TypeVar

from pydantic import BaseModel

from unique_client.core.requestor import APIRequestor
from unique_client.core.utils import retry_on_error
from unique_client.protocols import RequestContextProtocol

# Generic type for Pydantic models
T = TypeVar("T", bound=BaseModel)

retry_dict = {
    "error_messages": [
        "problem proxying the request",
        "Upstream service reached a hard timeout",
        "You can retry your request",
        "Internal server error",
        "Connection aborted",
    ],
    "max_retries": 3,
    "backoff_factor": 2,
    "initial_delay": 1,
    "should_retry_5xx": True,
}


class APIResource:
    """
    Base class for all API resources in unique_client.

    This class enforces the Pydantic approach:
    - Input parameters must be Pydantic models (with model_dump() support)
    - Output responses are always parsed as Pydantic models
    - All methods use the stored RequestContextProtocol for automatic header and URL generation
    """

    OBJECT_NAME: ClassVar[str]

    def __init__(self, context: RequestContextProtocol) -> None:
        """
        Initialize the API resource with a request context.

        Args:
            context: RequestContextProtocol with auth, config, and additional headers
        """
        self.context = context

    @retry_on_error(**retry_dict)
    def _request(
        self,
        method_: str,
        endpoint_: str,
        model_class: Type[T],
        params: Optional[BaseModel] = None,
    ) -> T:
        """
        Make a request using the stored RequestContextProtocol for automatic header and URL generation.

        This method enforces the Pydantic approach:
        - Params must be Pydantic models with model_dump() support
        - Response is always parsed as the specified Pydantic model class

        Args:
            method_: HTTP method (get, post, patch, delete)
            endpoint_: API endpoint (e.g. "/content/search")
            model_class: Pydantic model class to parse the response
            params: Optional Pydantic model for request parameters

        Returns:
            Parsed response as the specified Pydantic model

        Raises:
            Various API errors if the request fails
        """
        # Convert Pydantic model to dict for serialization
        params_dict = (
            None
            if params is None
            else params.model_dump(by_alias=True, exclude_none=True)
        )

        # Let RequestContextProtocol build the full URL and headers
        full_url = self.context.build_full_url(endpoint_)
        headers = self.context.build_headers(method_)

        rbody, rcode, rheaders = APIRequestor.request(
            method_, full_url, headers, params_dict
        )

        # Let the API resource interpret the response with mandatory Pydantic model
        return APIRequestor.interpret_response_with_model(
            rbody, rcode, rheaders, model_class
        )

    @retry_on_error(**retry_dict)
    async def _request_async(
        self,
        method_: str,
        endpoint_: str,
        model_class: Type[T],
        params: Optional[BaseModel] = None,
    ) -> T:
        """
        Make an async request using the stored RequestContextProtocol for automatic header and URL generation.

        This method enforces the Pydantic approach:
        - Params must be Pydantic models with model_dump() support
        - Response is always parsed as the specified Pydantic model class

        Args:
            method_: HTTP method (get, post, patch, delete)
            endpoint_: API endpoint (e.g. "/content/search")
            model_class: Pydantic model class to parse the response
            params: Optional Pydantic model for request parameters

        Returns:
            Parsed response as the specified Pydantic model

        Raises:
            Various API errors if the request fails
        """
        # Convert Pydantic model to dict for serialization
        params_dict = (
            None
            if params is None
            else params.model_dump(by_alias=True, exclude_none=True)
        )

        # Let RequestContextProtocol build the full URL and headers
        full_url = self.context.build_full_url(endpoint_)
        headers = self.context.build_headers(method_)

        rbody, rcode, rheaders = await APIRequestor.request_async(
            method_, full_url, headers, params_dict
        )

        # Let the API resource interpret the response with mandatory Pydantic model
        return APIRequestor.interpret_response_with_model(
            rbody, rcode, rheaders, model_class
        )
