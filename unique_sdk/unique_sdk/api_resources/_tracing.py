import logging
from datetime import datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    Literal,
    NotRequired,
    Optional,
    Unpack,
    cast,
)
from urllib.parse import quote_plus

import unique_sdk._error as error_types
from unique_sdk._api_resource import APIResource
from unique_sdk._request_options import RequestOptions

log = logging.getLogger(__name__)


class Span(APIResource["Span"]):
    """
    This object represents a tracing span. Use it to instrument your application for observability.
    """

    OBJECT_NAME: ClassVar[Literal["span"]] = "span"

    class StartSpanParams(RequestOptions):
        name: str
        input: NotRequired[Optional[Dict[str, Any] | str]]
        output: NotRequired[Optional[Dict[str, Any] | str]]
        metadata: NotRequired[Optional[Dict[str, Any]]]

    class UpdateSpanParams(RequestOptions):
        input: NotRequired[Optional[Dict[str, Any] | str]]
        output: NotRequired[Optional[Dict[str, Any] | str]]
        metadata: NotRequired[Optional[Dict[str, Any]]]
        endSpan: NotRequired[Optional[bool]]

    id: str
    traceId: str
    name: str
    input: Optional[Dict[str, Any] | str]
    output: Optional[Dict[str, Any] | str]
    metadata: Optional[Dict[str, Any]]
    startTime: datetime
    endTime: Optional[datetime]

    @classmethod
    def start_span(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Span.StartSpanParams"],
    ) -> Optional["Span"]:
        """
        Starts a new span. Returns None if the API request fails due to permission or not found errors.
        """
        try:
            return cast(
                "Span",
                cls._static_request(
                    "post",
                    "/tracing/spans",
                    user_id,
                    company_id,
                    params=params,
                ),
            )
        except error_types.PermissionError as e:
            log.warning(
                f"Permission denied when starting span for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except error_types.APIError as e:
            # Treat 404 as non-critical for tracing
            if e.http_status == 404:
                log.warning(
                    f"API resource not found when starting span for user {user_id}, company {company_id}. Error: {e}"
                )
                return None
            log.warning(
                f"Error when starting span for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except Exception as e:
            log.warning(
                f"Unexpected error when starting span for user {user_id}, company {company_id}. Error: {e}",
                exc_info=log.isEnabledFor(logging.DEBUG)
            )
            return None

    @classmethod
    async def start_span_async(
        cls,
        user_id: str,
        company_id: str,
        **params: Unpack["Span.StartSpanParams"],
    ) -> Optional["Span"]:
        """
        Starts a new span. Returns None if the API request fails due to permission or not found errors.
        """
        try:
            return cast(
                "Span",
                await cls._static_request_async(
                    "post",
                    "/tracing/spans",
                    user_id,
                    company_id,
                    params=params,
                ),
            )
        except error_types.PermissionError as e:
            log.warning(
                f"Permission denied when starting span async for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except error_types.APIError as e:
            if e.http_status == 404:
                log.warning(
                    f"API resource not found when starting span async for user {user_id}, company {company_id}. Error: {e}"
                )
                return None
            log.warning(
                f"Error when starting span async for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except Exception as e:
            log.warning(
                f"Unexpected error when starting span async for user {user_id}, company {company_id}. Error: {e}",
                exc_info=log.isEnabledFor(logging.DEBUG)
            )
            return None

    @classmethod
    def update_span(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Span.UpdateSpanParams"],
    ) -> Optional["Span"]:
        """
        Updates an existing span. Returns None if the API request fails due to permission or not found errors.
        """
        url = f"/tracing/spans/{quote_plus(id)}"
        try:
            return cast(
                "Span",
                cls._static_request(
                    "patch",
                    url,
                    user_id,
                    company_id,
                    params=params,
                ),
            )
        except error_types.PermissionError as e:
            log.warning(
                f"Permission denied when updating span {id} for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except error_types.APIError as e:
            if e.http_status == 404:
                log.warning(
                    f"Span {id} not found when updating for user {user_id}, company {company_id}. Error: {e}"
                )
                return None
            log.warning(
                f"Error when updating span {id} for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except Exception as e:
            log.warning(
                f"Unexpected error when updating span {id} for user {user_id}, company {company_id}. Error: {e}",
                exc_info=log.isEnabledFor(logging.DEBUG)
            )
            return None

    @classmethod
    async def update_span_async(
        cls,
        user_id: str,
        company_id: str,
        id: str,
        **params: Unpack["Span.UpdateSpanParams"],
    ) -> Optional["Span"]:
        """
        Updates an existing span. Returns None if the API request fails due to permission or not found errors.
        """
        url = f"/tracing/spans/{quote_plus(id)}"
        try:
            return cast(
                "Span",
                await cls._static_request_async(
                    "patch",
                    url,
                    user_id,
                    company_id,
                    params=params,
                ),
            )
        except error_types.PermissionError as e:
            log.warning(
                f"Permission denied when updating span async {id} for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except error_types.APIError as e:
            if e.http_status == 404:
                log.warning(
                    f"Span {id} not found when updating async for user {user_id}, company {company_id}. Error: {e}"
                )
                return None
            log.warning(
                f"Error when updating span async {id} for user {user_id}, company {company_id}. Error: {e}"
            )
            return None
        except Exception as e:
            log.warning(
                f"Unexpected error when updating span async {id} for user {user_id}, company {company_id}. Error: {e}",
                exc_info=log.isEnabledFor(logging.DEBUG)
            )
            return None

    def update(
        self,
        user_id: str,
        company_id: str,
        **params: Unpack["Span.UpdateSpanParams"],
    ) -> Optional["Span"]:
        """
        Updates this span instance. Returns None if the API request fails due to permission or not found errors.
        """
        return self.update_span(user_id, company_id, self.id, **params)

    async def update_async(
        self,
        user_id: str,
        company_id: str,
        **params: Unpack["Span.UpdateSpanParams"],
    ) -> Optional["Span"]:
        """
        Updates this span instance. Returns None if the API request fails due to permission or not found errors.
        """
        return await self.update_span_async(user_id, company_id, self.id, **params)
