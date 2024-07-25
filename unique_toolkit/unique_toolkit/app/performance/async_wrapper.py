import asyncio
import warnings
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


def to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def async_warning(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        warnings.warn(
            f"The function '{func.__name__}' is not purely async. It uses a thread pool executor underneath, "
            "which may impact performance for CPU-bound operations.",
            RuntimeWarning,
            stacklevel=2,
        )
        return await func(*args, **kwargs)

    return wrapper
