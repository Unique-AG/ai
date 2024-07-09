import asyncio
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar('T')

def to_async(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper