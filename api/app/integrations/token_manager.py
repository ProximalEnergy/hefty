# token_manager.py
from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import TypedDict

import app.integrations.providers.tenaska as tenaska


class TokenResponse(TypedDict):
    access_token: str
    expires_in: int  # seconds
    token_type: str


class TokenManager:
    """
    In-memory, single-process token cache with double-checked locking.
    The provider-specific logic is injected via `fetch_token`.
    """

    def __init__(  # skip-star-syntax
        self,
        fetch_token: Callable[[], Awaitable[TokenResponse]],
        refresh_margin_s: int = 120,
        jitter_s: int = 30,
    ) -> None:
        self._fetch_token_cb = fetch_token
        self._refresh_margin_s = refresh_margin_s
        self._jitter_s = jitter_s

        self._token: str | None = None
        self._expiry: int = 0
        self._lock = asyncio.Lock()

    def _now(self) -> int:
        return int(time.time())

    def _needs_refresh(self, force: bool = False) -> bool:  # skip-star-syntax
        if self._token is None or force:
            return True
        jitter = random.randint(0, self._jitter_s) if self._jitter_s > 0 else 0
        return self._now() + self._refresh_margin_s + jitter >= self._expiry

    async def _refresh_under_lock(self) -> str:
        if not self._needs_refresh():
            assert self._token is not None  # noqa: S101
            return self._token
        resp = await self._fetch_token_cb()
        self._token = resp["access_token"]
        self._expiry = self._now() + int(resp.get("expires_in", 86400))
        return self._token

    async def get_token(self) -> str:
        if not self._needs_refresh():
            assert self._token is not None  # noqa: S101
            return self._token
        async with self._lock:
            if not self._needs_refresh():
                assert self._token is not None  # noqa: S101
                return self._token
            return await self._refresh_under_lock()

    async def force_refresh_and_get(self) -> str:
        async with self._lock:
            return await self._refresh_under_lock()


## PROVIDERS ##
@lru_cache(maxsize=1)
def get_tps_token_manager() -> TokenManager:
    # lru_cache returns the same instance within the process
    return TokenManager(fetch_token=tenaska.fetch_tps_token)
