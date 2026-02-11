"""Development endpoints for exploring PowerTools Platform (PTP) API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app import dependencies, utils
from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import TokenManager

router = APIRouter(
    prefix="/ptp",
    tags=["development-ptp"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get("/markets")
async def get_ptp_markets(
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Get available markets from PTP API.

    Returns:
        List of available markets.
    """
    try:
        token = await tps_token.get_token()
        result = await ptp_explorer.get_markets(token=token)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch markets: {exc}"
        ) from exc


@router.get("/markets/{market}/endpoints")
async def get_ptp_endpoints(
    market: str,
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Get available endpoints for a market.

    Args:
        market: Market name (e.g., ERCOTNodal).
        tps_token: Token manager for PTP API authentication.

    Returns:
        List of available endpoints for the market.
    """
    try:
        token = await tps_token.get_token()
        result = await ptp_explorer.get_endpoints(token=token, market=market)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch endpoints: {exc}"
        ) from exc


@router.get("/markets/{market}/endpoints/{endpoint}/schema")
async def get_ptp_endpoint_schema(
    market: str,
    endpoint: str,
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Get schema information for a specific endpoint.

    Args:
        market: Market name (e.g., ERCOTNodal).
        endpoint: Endpoint name.
        tps_token: Token manager for PTP API authentication.

    Returns:
        Schema information for the endpoint.
    """
    try:
        token = await tps_token.get_token()
        result = await ptp_explorer.get_endpoint_schema(
            token=token, market=market, endpoint=endpoint
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch schema: {exc}"
        ) from exc


@router.get("/markets/{market}/endpoints/{endpoint}/elements")
async def get_ptp_endpoint_elements(
    market: str,
    endpoint: str,
    viewport: str | None = Query(None, description="Viewport date (YYYY-MM-DD)"),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Get elements available for an endpoint.

    Args:
        market: Market name (e.g., ERCOTNodal).
        endpoint: Endpoint name.
        viewport: Optional viewport date (YYYY-MM-DD format).
        tps_token: Token manager for PTP API authentication.

    Returns:
        List of available elements for the endpoint.
    """
    try:
        token = await tps_token.get_token()
        result = await ptp_explorer.get_endpoint_elements(
            token=token, market=market, endpoint=endpoint, viewport=viewport
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch elements: {exc}"
        ) from exc


@router.get("/markets/{market}/endpoints/{endpoint}/data")
async def get_ptp_endpoint_data(
    market: str,
    endpoint: str,
    elements: list[str] | None = Query(
        None, description="Element identifiers to filter"
    ),
    begin: str | None = Query(None, description="Begin timestamp (ISO 8601 UTC)"),
    end: str | None = Query(None, description="End timestamp (ISO 8601 UTC)"),
    environment: str | None = Query(None, description="Environment filter"),
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Query data from an endpoint.

    Args:
        market: Market name (e.g., ERCOTNodal).
        endpoint: Endpoint name.
        elements: Optional list of element identifiers to filter.
        begin: Optional begin timestamp (ISO 8601 UTC).
        end: Optional end timestamp (ISO 8601 UTC).
        environment: Optional environment filter.
        tps_token: Token manager for PTP API authentication.

    Returns:
        Data from the endpoint.
    """
    try:
        token = await tps_token.get_token()
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market=market,
            endpoint=endpoint,
            elements=elements,
            begin=begin,
            end=end,
            environment=environment,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch data: {exc}"
        ) from exc


@router.get("/explore")
async def explore_ptp_api(
    tps_token: TokenManager = Depends(dependencies.tps_token_mgr_async),
):
    """Explore the PTP API structure and return a comprehensive summary.

    This endpoint queries the API to understand available markets, endpoints,
    and their schemas. Useful for development and debugging.

    Returns:
        Dictionary containing API structure summary.
    """
    try:
        result = await ptp_explorer.explore_ptp_api(token_manager=tps_token)
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to explore API: {exc}"
        ) from exc
