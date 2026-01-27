import functools
import logging
from typing import (
    Awaitable,
    Callable,
    Generic,
    Iterable,
    ParamSpec,
    Type,
    TypeVar,
    cast,
)

# Function types
P = ParamSpec("P")
R = TypeVar("R")


_logger = logging.getLogger(__name__)


class Result(Generic[R]):
    def __init__(
        self,
        success: bool,
        result: R | None = None,
        exception: Exception | None = None,
    ) -> None:
        self._success = success
        self._result = result
        self._exception = exception

    @property
    def exception(self) -> Exception | None:
        return self._exception

    @property
    def success(self) -> bool:
        return self._success

    def unpack(self, default: R | None = None) -> R:
        return cast(R, self._result) if self.success else cast(R, default)

    def __str__(self) -> str:
        return (
            f"Success: {str(self._result)}"
            if self.success
            else f"Failure: {str(self._exception)}"
        )


class SafeTaskExecutor:
    """
    Execute function calls "safely": exceptions are caught and logged,
    and the function result is returned as a `Result` object.

    Several parameters are available to customize the behavior of the executor:
    - `exceptions`: a list of exceptions that should be caught and logged
    - `ignored_exceptions`: a list of exceptions that should be passed through
    - `log_exceptions`: whether to log exceptions
    - `log_exc_info`: whether to log exception info
    - `logger`: a logger to use for logging


    Usage:
    ```python
    executor = SafeTaskExecutor(
        exceptions=(ValueError,),
        ignored_exceptions=(KeyError,),
    )

    executor.execute(failing_function, "test")

    executor.execute_async(async_failing_function, "test")
    ```
    """

    def __init__(
        self,
        exceptions: Iterable[Type[Exception]] = (Exception,),
        ignored_exceptions: Iterable[Type[Exception]] = (),
        log_exceptions: bool = True,
        log_exc_info: bool = True,
        logger: logging.Logger | None = None,
    ) -> None:
        self._exceptions = tuple(exceptions)
        self._ignored_exceptions = tuple(ignored_exceptions)
        self._log_exceptions = log_exceptions
        self._log_exc_info = log_exc_info
        self._logger = logger or _logger

    def execute(
        self, f: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> Result[R]:
        try:
            return Result(True, f(*args, **kwargs))
        except self._exceptions as e:
            if isinstance(e, self._ignored_exceptions):
                raise e
            if self._log_exceptions:
                self._logger.error(
                    f"Error in {f.__name__}: {e}", exc_info=self._log_exc_info
                )
            return Result(False, exception=e)

    async def execute_async(
        self, f: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs
    ) -> Result[R]:
        try:
            return Result(True, await f(*args, **kwargs))
        except self._exceptions as e:
            if isinstance(e, self._ignored_exceptions):
                raise e
            if self._log_exceptions:
                self._logger.error(
                    f"Error in {f.__name__}: {e}", exc_info=self._log_exc_info
                )
            return Result(False, exception=e)


def safe_execute(f: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> Result[R]:
    """
    Execute a function call "safely": exceptions are caught and logged,
    and the function result is returned as a `Result` object.

    Usage:
    ```python
    def failing_function(a : str) -> int:
        raise ValueError(a)

    result = safe_execute(failing_function, "test")
    print(result)
    >> Failure: ValueError('test')

    result.success
    >> False

    result.unpack()
    >> None

    result.exception
    >> ValueError('test')

    result.unpack(default=1)
    >> 1
    ```

    ```python
    def succeeding_function(a : str):
        return a


    result = safe_execute(succeeding_function, "test")

    print(result)
    >> Success: test

    result.success
    >> True

    result.unpack()
    >> 'test'

    result.exception
    >> None
    ```
    """
    return SafeTaskExecutor().execute(f, *args, **kwargs)


async def safe_execute_async(
    f: Callable[P, Awaitable[R]], *args: P.args, **kwargs: P.kwargs
) -> Result[R]:
    """
    Equivalent to `safe_execute` for async functions.
    """
    return await SafeTaskExecutor().execute_async(f, *args, **kwargs)


FailureReturnType = TypeVar("FailureReturnType")


def failsafe(
    failure_return_value: FailureReturnType, exceptions: Iterable[Type[Exception]] = (Exception,),
    ignored_exceptions: Iterable[Type[Exception]] = (),
    log_exceptions: bool = True,
    log_exc_info: bool = True,
    logger: logging.Logger | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R | FailureReturnType]]:
    """
    Decorator that executes sync functions with failsafe behavior: exceptions are caught and logged,
    and a fallback return value is returned on failure instead of raising the exception.

    Parameters are the same as SafeTaskExecutor plus:
    - `failure_return_value`: value to return when an exception occurs

    Usage:
    ```python
    @failsafe(
        failure_return_value="default",
        exceptions=(ValueError,),
        ignored_exceptions=(KeyError,),
    )
    def failing_function(a: str) -> str:
        raise ValueError(a)


    result = failing_function("test")
    # Returns "default" instead of raising ValueError
    ```
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R | FailureReturnType]:
        executor = SafeTaskExecutor(
            exceptions=exceptions,
            ignored_exceptions=ignored_exceptions,
            log_exceptions=log_exceptions,
            log_exc_info=log_exc_info,
            logger=logger,
        )

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R | FailureReturnType:
            result = executor.execute(func, *args, **kwargs)
            return result.unpack(default=cast(R, failure_return_value))

        return sync_wrapper

    return decorator


def failsafe_async(
    failure_return_value: FailureReturnType,
    exceptions: Iterable[Type[Exception]] = (Exception,),
    ignored_exceptions: Iterable[Type[Exception]] = (),
    log_exceptions: bool = True,
    log_exc_info: bool = True,
    logger: logging.Logger | None = None,
) -> Callable[
    [Callable[P, Awaitable[R]]], Callable[P, Awaitable[R | FailureReturnType]]
]:
    """
    Decorator that executes async functions with failsafe behavior: exceptions are caught and logged,
    and a fallback return value is returned on failure instead of raising the exception.

    Parameters are the same as SafeTaskExecutor plus:
    - `failure_return_value`: value to return when an exception occurs

    Usage:
    ```python
    @failsafe_async(
        failure_return_value=[],
        exceptions=(ValueError,),
        ignored_exceptions=(KeyError,),
    )
    async def async_failing_function(a: str) -> list:
        raise ValueError(a)


    result = await async_failing_function("test")
    # Returns [] instead of raising ValueError
    ```
    """

    def decorator(
        func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R | FailureReturnType]]:
        executor = SafeTaskExecutor(
            exceptions=exceptions,
            ignored_exceptions=ignored_exceptions,
            log_exceptions=log_exceptions,
            log_exc_info=log_exc_info,
            logger=logger,
        )

        @functools.wraps(func)
        async def async_wrapper(
            *args: P.args, **kwargs: P.kwargs
        ) -> R | FailureReturnType:
            result = await executor.execute_async(func, *args, **kwargs)
            return result.unpack(default=cast(R, failure_return_value))

        return async_wrapper

    return decorator
