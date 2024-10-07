import asyncio
import functools
import logging
import os
import random
import re
import sys
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast, overload

from typing_extensions import TYPE_CHECKING, Type

import unique_sdk  # noqa: F401
from unique_sdk._error import APIError

if TYPE_CHECKING:
    from unique_sdk._unique_object import UniqueObject
    from unique_sdk._unique_response import UniqueResponse

UNIQUE_LOG = os.environ.get("UNIQUE_LOG")

logger: logging.Logger = logging.getLogger("unique")


def _console_log_level():
    if unique_sdk.log in ["debug", "info"]:
        return unique_sdk.log
    if UNIQUE_LOG in ["debug", "info"]:
        return UNIQUE_LOG
    return None


def log_debug(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() == "debug":
        print(msg, file=sys.stderr)
    logger.debug(msg)


def log_info(message, **params):
    msg = logfmt(dict(message=message, **params))
    if _console_log_level() in ["debug", "info"]:
        print(msg, file=sys.stderr)
    logger.info(msg)


def logfmt(props):
    def fmt(key, val):
        # Handle case where val is a bytes or bytesarray
        if hasattr(val, "decode"):
            val = val.decode("utf-8")
        # Check if val is already a string to avoid re-encoding into
        # ascii. Since the code is sent through 2to3, we can't just
        # use unicode(val, encoding='utf8') since it will be
        # translated incorrectly.
        if not isinstance(val, str):
            val = str(val)
        if re.search(r"\s", val):
            val = repr(val)
        # key should already be a string
        if re.search(r"\s", key):
            key = repr(key)
        return "{key}={val}".format(key=key, val=val)

    return " ".join([fmt(key, val) for key, val in sorted(props.items())])


def get_object_classes():
    # This is here to avoid a circular dependency
    from unique_sdk._object_classes import OBJECT_CLASSES

    return OBJECT_CLASSES


Resp = Union["UniqueResponse", Dict[str, Any], List["Resp"]]


@overload
def convert_to_unique_object(
    resp: Union["UniqueResponse", Dict[str, Any]],
    user_id: Optional[str],
    company_id: Optional[str],
    params: Optional[Dict[str, Any]] = None,
    klass_: Optional[Type["UniqueObject"]] = None,
) -> "UniqueObject": ...


@overload
def convert_to_unique_object(
    resp: List[Resp],
    user_id: Optional[str],
    company_id: Optional[str],
    params: Optional[Dict[str, Any]] = None,
    klass_: Optional[Type["UniqueObject"]] = None,
) -> List["UniqueObject"]: ...


def convert_to_unique_object(
    resp: Resp,
    user_id: Optional[str],
    company_id: Optional[str],
    params: Optional[Dict[str, Any]] = None,
    klass_: Optional[Type["UniqueObject"]] = None,
) -> Union["UniqueObject", List["UniqueObject"]]:
    # If we get a UniqueResponse, we'll want to return a
    # UniqueObject with the last_response field filled out with
    # the raw API response information
    unique_response = None

    # This is here to avoid a circular dependency
    from unique_sdk._unique_object import UniqueObject
    from unique_sdk._unique_response import UniqueResponse

    if isinstance(resp, UniqueResponse):
        unique_response = resp
        resp = cast(Resp, unique_response.data)

    if isinstance(resp, list):
        return [
            convert_to_unique_object(
                cast("Union[UniqueResponse, Dict[str, Any]]", i),
                user_id,
                company_id,
                klass_=klass_,
            )
            for i in resp
        ]
    elif isinstance(resp, dict) and not isinstance(resp, UniqueObject):
        resp = resp.copy()
        klass_name = resp.get("object")
        if isinstance(klass_name, str):
            klass = get_object_classes().get(klass_name, UniqueObject)
        elif klass_ is not None:
            klass = klass_
        else:
            klass = UniqueObject

        obj = klass.construct_from(
            resp,
            user_id,
            company_id,
            last_response=unique_response,
        )

        # We only need to update _retrieve_params when special params were
        # actually passed. Otherwise, leave it as is as the list / search result
        # constructors will instantiate their own params.
        if (
            params is not None
            and hasattr(obj, "object")
            and (
                (getattr(obj, "object") == "list")
                or (getattr(obj, "object") == "search_result")
            )
        ):
            obj._retrieve_params = params

        return obj
    else:
        return cast("UniqueObject", resp)


class class_method_variant(object):
    def __init__(self, class_method_name):
        self.class_method_name = class_method_name

    T = TypeVar("T")

    method: Any

    def __call__(self, method: T) -> T:
        T = TypeVar("T")
        self.method = method
        return cast(T, self)

    def __get__(self, obj, objtype: Optional[Type[Any]] = None):
        @functools.wraps(self.method)
        def _wrapper(*args, **kwargs):
            if obj is not None:
                # Method was called as an instance method, e.g.
                # instance.method(...)
                return self.method(obj, *args, **kwargs)
            elif len(args) > 0 and objtype is not None and isinstance(args[0], objtype):
                # Method was called as a class method with the instance as the
                # first argument, e.g. Class.method(instance, ...) which in
                # Python is the same thing as calling an instance method
                return self.method(args[0], *args[1:], **kwargs)
            else:
                # Method was called as a class method, e.g. Class.method(...)
                class_method = getattr(objtype, self.class_method_name)
                return class_method(*args, **kwargs)

        return _wrapper


def retry_on_error(
    max_retries=3,
    initial_delay=1,
    backoff_factor=2,
    error_message="problem proxying the request",
    error_class=APIError
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            attempts = 0
            while attempts < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Check if error message contains the specific text
                    if error_message not in str(e):
                        raise e  # Raise the error if it doesn't contain the specific message

                    attempts += 1
                    if attempts >= max_retries:
                        raise error_class(f"Failed after {max_retries} attempts: {e}")

                    # Calculate exponential backoff with some randomness (jitter)
                    delay = initial_delay * (backoff_factor ** (attempts - 1))
                    jitter = random.uniform(0, 0.1 * delay)
                    await asyncio.sleep(delay + jitter)

        def sync_wrapper(*args, **kwargs) -> Any:
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Check if error message contains the specific text
                    if error_message not in str(e):
                        raise e  # Raise the error if it doesn't contain the specific message

                    attempts += 1
                    if attempts >= max_retries:
                        raise error_class(f"Failed after {max_retries} attempts: {e}")

                    # Calculate exponential backoff with some randomness (jitter)
                    delay = initial_delay * (backoff_factor ** (attempts - 1))
                    jitter = random.uniform(0, 0.1 * delay)
                    time.sleep(delay + jitter)

        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
