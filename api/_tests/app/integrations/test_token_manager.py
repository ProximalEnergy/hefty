import httpx
import pytest
from app.integrations.token_manager import TokenManager, TokenResponse
from fastapi import HTTPException, status


@pytest.mark.asyncio
async def test_token_manager_maps_upstream_5xx_to_failed_dependency() -> None:
    """Map upstream 5xx auth failures to failed dependency."""

    async def fetch_token() -> TokenResponse:
        request = httpx.Request("GET", "https://tenaska.test/token")
        response = httpx.Response(503, request=request)
        raise httpx.HTTPStatusError(
            "Service unavailable",
            request=request,
            response=response,
        )

    token_manager = TokenManager(fetch_token=fetch_token)

    with pytest.raises(HTTPException) as exc_info:
        await token_manager.get_token()

    assert getattr(exc_info.value, "status_code") == (status.HTTP_424_FAILED_DEPENDENCY)
    assert getattr(exc_info.value, "detail") == (
        "We weren't able to authenticate with Tenaska due to an issue on Tenaska's end"
    )


@pytest.mark.asyncio
async def test_token_manager_maps_network_error_to_failed_dependency() -> None:
    """Map auth network failures to failed dependency."""

    async def fetch_token() -> TokenResponse:
        request = httpx.Request("GET", "https://tenaska.test/token")
        raise httpx.ReadTimeout("Timed out", request=request)

    token_manager = TokenManager(fetch_token=fetch_token)

    with pytest.raises(HTTPException) as exc_info:
        await token_manager.get_token()

    assert getattr(exc_info.value, "status_code") == (status.HTTP_424_FAILED_DEPENDENCY)
    assert getattr(exc_info.value, "detail") == (
        "We weren't able to authenticate with Tenaska due to an issue on Tenaska's end"
    )
