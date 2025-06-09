"""
API Requestor for Unique SDK v2

This module handles the HTTP implementation details for making requests to the Unique API.
It's designed to work with pre-built headers and configuration.

The requestor enforces the strict Pydantic approach:
- Input params must be Pydantic models (serialized via model_dump())
- Response parsing is done via Pydantic model_validate_json()
- No legacy UniqueResponse dependencies
"""

import json
from typing import Any, Dict, NoReturn, Optional, Type, TypeVar
from urllib.parse import urlencode

from pydantic import BaseModel

import unique_client
from unique_client.core import errors as _error
from unique_client.core import utils as _util
from unique_client.core.http_clients import (
    HTTPClientProtocol,
    HTTPHeaders,
    HTTPResponse,
    get_async_client,
    get_default_client,
)

# Generic type for Pydantic models
T = TypeVar("T", bound=BaseModel)


class APIRequestor:
    """
    Static API requestor for making HTTP requests to the Unique API.
    All methods are class methods and no instance creation is required.

    This class enforces the strict Pydantic approach for consistent type safety:
    - Input parameters must be Pydantic models (serialized via model_dump())
    - Response deserialization via Pydantic model_validate_json()
    - Direct JSON parsing without UniqueResponse wrapper
    """

    _http_client: Optional[HTTPClientProtocol] = None

    @classmethod
    def _get_http_client(cls) -> HTTPClientProtocol:
        """Get or initialize the HTTP client."""
        if cls._http_client is None:
            if (
                hasattr(unique_client, "default_http_client")
                and unique_client.default_http_client
            ):
                cls._http_client = unique_client.default_http_client
            else:
                # Use our improved factory-based HTTP client
                async_fallback = get_async_client()
                if async_fallback:
                    cls._http_client = get_default_client(
                        async_fallback_client=async_fallback
                    )
                else:
                    cls._http_client = get_default_client()
        return cls._http_client

    @classmethod
    def request(
        cls,
        method: str,
        full_url: str,
        headers: HTTPHeaders,
        params: Optional[Dict[str, Any]] = None,
    ) -> HTTPResponse:
        """
        Make a synchronous HTTP request.

        Args:
            method: HTTP method (get, post, patch, delete)
            full_url: Complete URL for the request
            headers: HTTP headers dictionary
            params: Request parameters as dict (from Pydantic model_dump())

        Returns:
            Tuple of (response_body, status_code, response_headers)
        """
        return cls._make_request(method, full_url, headers, params, is_async=False)

    @classmethod
    async def request_async(
        cls,
        method: str,
        full_url: str,
        headers: HTTPHeaders,
        params: Optional[Dict[str, Any]] = None,
    ) -> HTTPResponse:
        """
        Make an asynchronous HTTP request.

        Args:
            method: HTTP method (get, post, patch, delete)
            full_url: Complete URL for the request
            headers: HTTP headers dictionary
            params: Request parameters as dict (from Pydantic model_dump())

        Returns:
            Tuple of (response_body, status_code, response_headers)
        """
        return await cls._make_request(method, full_url, headers, params, is_async=True)

    @classmethod
    def _make_request(
        cls,
        method: str,
        full_url: str,
        headers: HTTPHeaders,
        params: Optional[Dict[str, Any]] = None,
        is_async: bool = False,
    ) -> HTTPResponse:
        """Core request logic shared between sync and async methods."""
        method = method.lower()
        final_url, request_headers, post_data = cls._prepare_request(
            method, full_url, headers, params
        )

        _util.log_info("Request to Unique", method=method, path=final_url)
        _util.log_debug(
            "Request details",
            data=post_data,
            headers=request_headers,
        )

        client = cls._get_http_client()

        if is_async:
            return client.request_async(method, final_url, request_headers, post_data)
        else:
            rcontent, rcode, rheaders = client.request(
                method, final_url, request_headers, post_data
            )

            _util.log_info("Unique response", path=final_url, status=rcode)
            _util.log_debug("Unique response body", body=rcontent)

            if "Request-Id" in rheaders:
                _util.log_debug("Unique request id", request_id=rheaders["Request-Id"])

            return rcontent, rcode, rheaders

    @classmethod
    def _prepare_request(
        cls,
        method: str,
        full_url: str,
        headers: HTTPHeaders,
        params: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, HTTPHeaders, Optional[Dict[str, Any]]]:
        """
        Prepare request URL, headers, and data.

        Args:
            method: HTTP method
            full_url: Complete URL
            headers: HTTP headers
            params: Request parameters as dict (already serialized from Pydantic model)

        Returns:
            Tuple of (final_url, request_headers, post_data)
        """
        # Use the full URL directly
        final_url = full_url

        # Use provided headers directly
        request_headers = dict(headers)

        # Handle parameters (already serialized from Pydantic models)
        post_data = None
        if params:
            if method in ["get", "delete"]:
                # Add params to URL for GET/DELETE
                query_string = urlencode(params, doseq=True)
                separator = "&" if "?" in final_url else "?"
                final_url = f"{final_url}{separator}{query_string}"
            else:
                # Use params as JSON body for POST/PATCH
                post_data = params

        return final_url, request_headers, post_data

    @classmethod
    def interpret_response_with_model(
        cls,
        rbody: bytes,
        rcode: int,
        rheaders: HTTPHeaders,
        model_class: Type[T],
    ) -> T:
        """
        Interpret response and convert to Pydantic model.

        This is the primary method for the strict Pydantic approach, providing
        type safety and automatic validation without UniqueResponse wrapper.

        Args:
            rbody: Raw response body (bytes)
            rcode: HTTP status code
            rheaders: Response headers
            model_class: Pydantic model class for parsing response

        Returns:
            Parsed and validated Pydantic model instance

        Raises:
            Various API errors if the request failed or validation fails
        """
        # Decode response body if needed
        if hasattr(rbody, "decode"):
            rbody_str = rbody.decode("utf-8")
        else:
            rbody_str = str(rbody)

        # Check for errors first
        if not (200 <= rcode < 300):
            # Parse response as JSON to extract error information
            try:
                response_data = json.loads(rbody_str)
            except (json.JSONDecodeError, TypeError):
                # If we can't parse the response, raise a generic API error
                raise _error.APIError(
                    f"Invalid response from API: {rbody_str!r} (HTTP response code was {rcode})",
                    rbody_str,
                    rcode,
                    None,
                )

            cls._handle_error_response(rbody_str, rcode, response_data, rheaders)

        # Parse successful response using Pydantic
        return model_class.model_validate_json(rbody_str)

    @classmethod
    def _handle_error_response(
        cls,
        rbody: str,
        rcode: int,
        response_data: Dict[str, Any],
        rheaders: HTTPHeaders,
    ) -> NoReturn:
        """
        Handle API error responses with direct JSON parsing.

        Args:
            rbody: Raw response body as string
            rcode: HTTP status code
            response_data: Parsed JSON response data
            rheaders: Response headers
        """
        try:
            error_data = response_data["error"]
        except (KeyError, TypeError):
            raise _error.APIError(
                f"Invalid response object from API: {rbody!r} (HTTP response code was {rcode})",
                rbody,
                rcode,
                response_data,
            )

        # Log error details
        _util.log_info(
            "Unique API error received",
            error_code=error_data.get("code"),
            error_type=error_data.get("type"),
            error_message=error_data.get("message"),
            error_param=error_data.get("param"),
        )

        # Extract error details
        error_message = error_data.get("message")
        error_param = error_data.get("param")
        error_code = error_data.get("code")

        # Map status codes to specific errors
        if rcode == 429:
            raise _error.RateLimitError(
                error_message, rbody, rcode, response_data, rheaders
            )
        elif rcode in [400, 404]:
            raise _error.InvalidRequestError(
                error_message,
                error_param,
                error_code,
                rbody,
                rcode,
                response_data,
                rheaders,
            )
        elif rcode == 401:
            raise _error.AuthenticationError(
                error_message, rbody, rcode, response_data, rheaders
            )
        elif rcode == 402:
            raise _error.CardError(
                error_message,
                error_param,
                error_code,
                rbody,
                rcode,
                response_data,
                rheaders,
            )
        elif rcode == 403:
            raise _error.PermissionError(
                error_message, rbody, rcode, response_data, rheaders
            )
        elif rcode >= 500:
            raise _error.APIError(error_message, rbody, rcode, response_data, rheaders)
        else:
            raise _error.APIError(error_message, rbody, rcode, response_data, rheaders)
