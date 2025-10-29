# providers/tenaska.py

from typing import TYPE_CHECKING

import httpx
from app import settings

if TYPE_CHECKING:
    from app.integrations.token_manager import TokenResponse


async def fetch_tps_token() -> "TokenResponse":
    username = settings.TENASKA_CLIENT_ID
    password = settings.TENASKA_CLIENT_SECRET
    token_url = settings.TENASKA_TOKEN_URL
    if not username or not password or not token_url:
        raise RuntimeError(
            "Missing TENASKA_CLIENT_ID or TENASKA_CLIENT_SECRET or TENASKA_TOKEN_URL env vars"
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        # This provider expects GET + BasicAuth
        resp = await client.get(
            token_url,
            auth=httpx.BasicAuth(username, password),
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    # According to your working snippet, token is under "data"
    access_token = data["data"]

    # If Tenaska returns an explicit lifetime, prefer it. Otherwise assume 24h.
    # Common alt fields to probe: "expiresIn", "ttl", "ttlSeconds"
    expires_in = int(data.get("expiresIn", 86400))

    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "token_type": "Bearer",
    }
