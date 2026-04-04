from __future__ import annotations

import asyncio
from collections.abc import Awaitable

_loop = asyncio.new_event_loop()


def run_in_loop[T](coro: Awaitable[T]) -> T:
    """Run a coroutine on a single, long-lived event loop."""
    return _loop.run_until_complete(coro)
