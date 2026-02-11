# ptp_explorer.py
"""Utility functions to explore the PowerTools Platform (PTP) API structure."""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from app.integrations.token_manager import TokenManager


def _response_json_dict(*, response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("Expected JSON object response")
    return cast(dict[str, Any], payload)


async def get_markets(*, token: str) -> dict[str, Any]:
    """Get available markets from PTP API.

    Uses the new /ptp API structure. The old /v1/markets routes will be
    deprecated January 31, 2026 and sunset January 31, 2027.

    Args:
        token: Bearer token for authentication.

    Returns:
        JSON response containing available markets.
    """
    # Use new /ptp API structure
    url = "https://api.ptp.energy/ptp"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return _response_json_dict(response=response)


async def get_endpoints(
    *,
    token: str,
    market: str = "ERCOTNodal",
) -> dict[str, Any]:
    """Get available endpoints for a market.

    Uses the new /ptp API structure. The old /v1/markets routes will be
    deprecated January 31, 2026 and sunset January 31, 2027.

    Args:
        token: Bearer token for authentication.
        market: Market name (default: ERCOTNodal).

    Returns:
        JSON response containing available endpoints. The response structure
        is slightly different in the new API - endpoints are nested under
        the market's "endpoints" key in the "data" object.
    """
    # Use new /ptp API structure
    url = f"https://api.ptp.energy/ptp/{market}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = _response_json_dict(response=response)
        # New API returns market info with endpoints nested, but we want
        # to maintain backward compatibility with the old response format
        # The old API returned {"data": [endpoint1, endpoint2, ...]}
        # The new API returns {"data": {"endpoints": [endpoint1, ...], ...}}
        if "data" in data and "endpoints" in data["data"]:
            # Return in old format for backward compatibility
            return {"data": data["data"]["endpoints"]}
        return data


async def get_endpoint_schema(
    *,
    token: str,
    market: str = "ERCOTNodal",
    endpoint: str,
) -> dict[str, Any]:
    """Get schema information for a specific endpoint.

    Uses the new /ptp API structure. The old /v1/markets routes will be
    deprecated January 31, 2026 and sunset January 31, 2027.

    Args:
        token: Bearer token for authentication.
        market: Market name (default: ERCOTNodal).
        endpoint: Endpoint name.

    Returns:
        JSON response containing endpoint schema.
    """
    # Use new /ptp API structure
    url = f"https://api.ptp.energy/ptp/{market}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return _response_json_dict(response=response)


async def get_endpoint_elements(
    *,
    token: str,
    market: str = "ERCOTNodal",
    endpoint: str,
    viewport: str | None = None,
) -> dict[str, Any]:
    """Get elements available for an endpoint.

    Uses the new /ptp API structure. The old /v1/markets routes will be
    deprecated January 31, 2026 and sunset January 31, 2027.

    Args:
        token: Bearer token for authentication.
        market: Market name (default: ERCOTNodal).
        endpoint: Endpoint name.
        viewport: Optional viewport date (YYYY-MM-DD format). Note: New API
            uses 'begin' and 'end' parameters instead.

    Returns:
        JSON response containing available elements.
    """
    # Use new /ptp API structure
    url = f"https://api.ptp.energy/ptp/{market}/{endpoint}/elements"
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, str] = {}
    # New API uses begin/end instead of viewport, but keeping viewport
    # for backward compatibility
    if viewport:
        # Convert viewport (YYYY-MM-DD) to begin/end for new API
        params["begin"] = viewport
        params["end"] = viewport

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        # Elements endpoint may return 404 for some endpoints
        if response.status_code == 404:
            return {"data": [], "error": "404 Not Found"}
        response.raise_for_status()
        return _response_json_dict(response=response)


async def get_endpoint_data(
    *,
    token: str,
    market: str = "ERCOTNodal",
    endpoint: str,
    elements: list[str] | None = None,
    begin: str | None = None,
    end: str | None = None,
    environment: str | None = None,
    data_points: list[str] | None = None,
) -> dict[str, Any]:
    """Query data from an endpoint.

    Uses the new /ptp API structure. The old /v1/markets routes will be
    deprecated January 31, 2026 and sunset January 31, 2027.

    Args:
        token: Bearer token for authentication.
        market: Market name (default: ERCOTNodal).
        endpoint: Endpoint name.
        elements: Optional list of element identifiers to filter.
        begin: Optional begin timestamp (ISO 8601 UTC).
        end: Optional end timestamp (ISO 8601 UTC).
        environment: Optional environment filter.
        data_points: Optional list of data point keynames to filter.

    Returns:
        JSON response containing endpoint data.
    """
    # Use new /ptp API structure
    url = f"https://api.ptp.energy/ptp/{market}/{endpoint}/query"
    headers = {"Authorization": f"Bearer {token}"}
    params: dict[str, str | list[str]] = {}

    # New API uses elementIdentifiers instead of elements
    if elements:
        params["elementIdentifiers"] = elements
    if begin:
        params["begin"] = begin
    if end:
        params["end"] = end
    if environment:
        params["environment"] = environment
    if data_points:
        params["dataPoints"] = data_points

    logger = logging.getLogger(__name__)

    # httpx handles array params by repeating the parameter name
    # e.g., elementIdentifiers=id1&elementIdentifiers=id2
    # This should work with PTP API, but let's verify the actual URL
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Build request to see the actual URL httpx will use
        request = client.build_request("GET", url, headers=headers, params=params)
        actual_url = str(request.url)
        logger.info(f"PTP API Request URL (httpx will use): {actual_url}")
        logger.info(f"PTP API Request params: {params}")

        response = await client.send(request)
        response.raise_for_status()
        return _response_json_dict(response=response)


async def explore_ptp_api(*, token_manager: TokenManager) -> dict[str, Any]:
    """Explore the PTP API structure and return a summary.

    This function queries the API to understand available markets, endpoints,
    and their schemas. Useful for development and debugging.

    Args:
        token_manager: TokenManager instance for authentication.

    Returns:
        Dictionary containing API structure summary.
    """
    token = await token_manager.get_token()

    result: dict[str, Any] = {
        "markets": {},
        "endpoints": {},
    }

    try:
        # Get available markets
        markets_response = await get_markets(token=token)
        result["markets"] = markets_response

        # For each market, get endpoints
        if "data" in markets_response:
            for market_entry in markets_response.get("data", []):
                market_name = market_entry.get("name") or market_entry.get("identifier")
                if not market_name:
                    continue

                try:
                    endpoints_response = await get_endpoints(
                        token=token, market=market_name
                    )
                    result["endpoints"][market_name] = {
                        "endpoints": endpoints_response,
                        "schemas": {},
                    }

                    # For each endpoint, get schema
                    if "data" in endpoints_response:
                        for endpoint_entry in endpoints_response.get("data", []):
                            endpoint_name = endpoint_entry.get(
                                "name"
                            ) or endpoint_entry.get("identifier")
                            if not endpoint_name:
                                continue

                            try:
                                schema_response = await get_endpoint_schema(
                                    token=token,
                                    market=market_name,
                                    endpoint=endpoint_name,
                                )
                                result["endpoints"][market_name]["schemas"][
                                    endpoint_name
                                ] = schema_response
                            except Exception as e:
                                result["endpoints"][market_name]["schemas"][
                                    endpoint_name
                                ] = {
                                    "error": str(e),
                                }
                except Exception as e:
                    result["endpoints"][market_name] = {"error": str(e)}
    except Exception as e:
        result["error"] = str(e)

    return result
