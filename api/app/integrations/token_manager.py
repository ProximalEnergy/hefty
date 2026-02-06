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
    """Token response from an integration provider."""

    access_token: str
    expires_in: int  # seconds
    token_type: str


class TokenManager:
    """
    In-memory, single-process token cache with double-checked locking.
    The provider-specific logic is injected via `fetch_token`.
    """

    def __init__(  # nosemgrep: python-enforce-keyword-only-args
        self,
        fetch_token: Callable[[], Awaitable[TokenResponse]],
        refresh_margin_s: int = 120,
        jitter_s: int = 30,
    ) -> None:
        """Initialize a token manager with refresh thresholds.

        Args:
            fetch_token: Coroutine that retrieves a fresh token payload.
            refresh_margin_s: Seconds before expiry to trigger refresh.
            jitter_s: Random jitter window in seconds to stagger refreshes.
        """
        self._fetch_token_cb = fetch_token
        self._refresh_margin_s = refresh_margin_s
        self._jitter_s = jitter_s

        self._token: str | None = None
        self._expiry: int = 0
        self._lock = asyncio.Lock()

    def _now(self) -> int:
        """Return current epoch time in seconds."""
        return int(time.time())

    def _needs_refresh(self, *, force: bool = False) -> bool:
        """Return whether the cached token should be refreshed.

        Args:
            force: Force refresh regardless of cached expiry.
        """
        if self._token is None or force:
            return True
        jitter = random.randint(0, self._jitter_s) if self._jitter_s > 0 else 0
        return self._now() + self._refresh_margin_s + jitter >= self._expiry

    async def _refresh_under_lock(self) -> str:
        """Refresh the token while holding the lock."""
        if not self._needs_refresh():
            assert self._token is not None  # noqa: S101
            return self._token
        resp = await self._fetch_token_cb()
        self._token = resp["access_token"]
        self._expiry = self._now() + int(resp.get("expires_in", 86400))
        return self._token

    async def get_token(self) -> str:
        """Return a valid token, refreshing if needed."""
        if not self._needs_refresh():
            assert self._token is not None  # noqa: S101
            return self._token
        async with self._lock:
            if not self._needs_refresh():
                assert self._token is not None  # noqa: S101
                return self._token
            return await self._refresh_under_lock()

    async def force_refresh_and_get(self) -> str:
        """Force a refresh and return the new token."""
        async with self._lock:
            return await self._refresh_under_lock()


## PROVIDERS ##
@lru_cache(maxsize=1)
def get_tps_token_manager() -> TokenManager:
    # lru_cache returns the same instance within the process
    """Return the cached TPS token manager."""
    return TokenManager(fetch_token=tenaska.fetch_tps_token)
