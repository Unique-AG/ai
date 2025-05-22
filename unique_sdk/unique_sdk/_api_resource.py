from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Literal,
    Mapping,
    Optional,
    Self,
    TypeVar,
)
from urllib.parse import quote_plus

from unique_sdk._api_requestor import APIRequestor
from unique_sdk._error import InvalidRequestError
from unique_sdk._unique_object import UniqueObject
from unique_sdk._util import convert_to_unique_object, retry_on_error

T = TypeVar("T", bound=UniqueObject)

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


class APIResource(UniqueObject, Generic[T]):
    OBJECT_NAME: ClassVar[str]

    def refresh(self, user_id, company_id) -> Self:
        return self._request_and_refresh(
            "get", self.instance_url(), user_id, company_id
        )

    async def refresh_async(self, user_id, company_id) -> Self:
        return await self._request_and_refresh_async(
            "get", self.instance_url(), user_id, company_id
        )

    @classmethod
    def class_url(cls) -> str:
        if cls == APIResource:
            raise NotImplementedError(
                "APIResource is an abstract class.  You should perform "
                "actions on its subclasses (e.g. Message)"
            )
        # Namespaces are separated in object names with periods (.) and in URLs
        # with forward slashes (/), so replace the former with the latter.
        base = cls.OBJECT_NAME.replace(".", "/")
        return "/%ss" % (base,)

    def instance_url(self) -> str:
        id = self.get("id")

        if not isinstance(id, str):
            raise InvalidRequestError(
                "Could not determine which URL to request: %s instance "
                "has invalid ID: %r, %s. ID should be of type `str` (or"
                " `unicode`)" % (type(self).__name__, id, type(id)),
                "id",
            )

        base = self.class_url()
        extn = quote_plus(id)
        return "%s/%s" % (base, extn)

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    def _request(
        self,
        method_,
        url_,
        user_id,
        company_id,
        headers=None,
        params=None,
    ) -> UniqueObject:
        obj = UniqueObject._request(
            self,
            method_,
            url_,
            user_id,
            company_id,
            headers,
            params,
        )

        if type(self) is type(obj):
            self.refresh_from(obj, user_id, company_id)
            return self
        else:
            return obj

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    async def _request_async(
        self,
        method_,
        url_,
        user_id,
        company_id,
        headers=None,
        params=None,
    ) -> UniqueObject:
        obj = await UniqueObject._request_async(
            self,
            method_,
            url_,
            user_id,
            company_id,
            headers,
            params,
        )

        if type(self) is type(obj):
            self.refresh_from(obj, user_id, company_id)
            return self
        else:
            return obj

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    def _request_and_refresh(
        self,
        method_: Literal["get", "post", "delete"],
        url_: str,
        user_id: str,
        company_id: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Self:
        obj = UniqueObject._request(
            self,
            method_,
            url_,
            user_id,
            company_id,
            headers,
            params,
        )

        self.refresh_from(obj, user_id, company_id)
        return self

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    async def _request_and_refresh_async(
        self,
        method_: Literal["get", "post", "delete"],
        url_: str,
        user_id: str,
        company_id: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Self:
        obj = await UniqueObject._request_async(
            self,
            method_,
            url_,
            user_id,
            company_id,
            headers,
            params,
        )

        self.refresh_from(obj, user_id, company_id)
        return self

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    @classmethod
    @retry_on_error(**retry_dict)
    def _static_request(
        cls,
        method_,
        url_,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        params=None,
    ) -> UniqueObject:
        params = None if params is None else params.copy()

        requestor = APIRequestor(user_id=user_id, company_id=company_id)

        response = requestor.request(method_, url_, params)
        return convert_to_unique_object(response, user_id, company_id, params)

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    @classmethod
    @retry_on_error(**retry_dict)
    async def _static_request_async(
        cls,
        method_,
        url_,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        params=None,
    ) -> UniqueObject:
        params = None if params is None else params.copy()

        requestor = APIRequestor(user_id=user_id, company_id=company_id)

        response = await requestor.request_async(method_, url_, params)
        return convert_to_unique_object(response, user_id, company_id, params)
