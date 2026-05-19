from collections.abc import Callable
from typing import TypeVar

from asgiref.sync import sync_to_async

T = TypeVar("T")


async def run_sync(callable: Callable[..., T], /, *args, **kwargs) -> T:
    "
    return await sync_to_async(callable, thread_sensitive=False)(*args, **kwargs)
