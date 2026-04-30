# ptp_explorer.py
"""Utility functions to explore the PowerTools Platform (PTP) API structure."""

from __future__ import annotations

import logging
from typing import Any, cast
from urllib.parse import urlencode

import httpx
from app.integrations.token_manager import TokenManager

# Safe URL length limit; many servers/proxies use 2048 or 8192.
# Stay well under to avoid InvalidURL from httpx (query component too long).
# httpx allows ~65K per component but encoding/encoding differences can cause
# underestimation; use conservative limit.
_MAX_QUERY_URL_LENGTH = 1500
_ELEM_BATCH_SIZE = 8
_ELEM_BATCH_SIZE_WITH_DATA_POINTS = 4
_DP_BATCH_SIZE = 10
_DP_BATCH_SIZE_WITH_ELEMENTS = 5
_MAX_BATCH_ELEMENTS = 1000
_MAX_BATCH_DATA_POINTS = 1000
_MAX_BATCH_REQUESTS = 1000


def _response_json_dict(*, response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("Expected JSON object response")
    return cast(dict[str, Any], payload)


def _estimate_query_url_length(*, url: str, params: dict[str, Any]) -> int:
    """Estimate total URL length including query string.

    Args:
        url: Base URL without query string.
        params: Query parameters (lists become repeated params).

    Returns:
        Estimated length of full URL with query string.
    """
    encoded = urlencode(params, doseq=True)
    return len(url) + 1 + len(encoded)  # url + "?" + query


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


def _merge_ptp_data_responses(*, responses: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple PTP query responses into one.

    When batching elements: concatenate data arrays.
    When batching data_points: merge dataPoints by element identifier.

    Args:
        responses: List of PTP API response dicts.

    Returns:
        Single merged response dict.
    """
    if not responses:
        return {"data": []}
    if len(responses) == 1:
        return responses[0]

    # Merge data arrays - dedupe by identifier, merge dataPoints
    merged_by_id: dict[str, dict[str, Any]] = {}
    for resp in responses:
        for entry in resp.get("data", []):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("identifier")
            if eid is None:
                continue
            if eid not in merged_by_id:
                merged_by_id[eid] = dict(entry)
                merged_by_id[eid]["dataPoints"] = list(entry.get("dataPoints", []))
            else:
                # Merge dataPoints (avoid duplicates by keyName)
                existing_keys = {
                    dp.get("keyName")
                    for dp in merged_by_id[eid]["dataPoints"]
                    if isinstance(dp, dict)
                }
                for dp in entry.get("dataPoints", []):
                    if isinstance(dp, dict) and dp.get("keyName") not in existing_keys:
                        merged_by_id[eid]["dataPoints"].append(dp)
                        existing_keys.add(dp.get("keyName"))

    result = dict(responses[0])
    result["data"] = list(merged_by_id.values())
    return result


async def _fetch_ptp_query(
    *,
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    params: dict[str, str | list[str]],
    logger: logging.Logger,
) -> dict[str, Any]:
    """Execute a single PTP query (GET)."""
    request = client.build_request("GET", url, headers=headers, params=params)
    logger.debug("PTP API Request URL: %s", str(request.url)[:200])
    response = await client.send(request)
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

    When the query URL would exceed length limits, batches elements or
    data_points into smaller requests and merges results.

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
    url = f"https://api.ptp.energy/ptp/{market}/{endpoint}/query"
    headers = {"Authorization": f"Bearer {token}"}
    logger = logging.getLogger(__name__)

    def _base_params() -> dict[str, str | list[str]]:
        p: dict[str, str | list[str]] = {}
        if begin:
            p["begin"] = begin
        if end:
            p["end"] = end
        if environment:
            p["environment"] = environment
        return p

    def _params_with(
        *,
        el: list[str] | None = None,
        dp: list[str] | None = None,
    ) -> dict[str, str | list[str]]:
        p = _base_params()
        if el:
            p["elementIdentifiers"] = el
        if dp:
            p["dataPoints"] = dp
        return p

    # Single request if URL is short enough
    params = _params_with(el=elements, dp=data_points)
    url_len = _estimate_query_url_length(url=url, params=params)
    if url_len <= _MAX_QUERY_URL_LENGTH:
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await _fetch_ptp_query(
                client=client,
                url=url,
                headers=headers,
                params=params,
                logger=logger,
            )

    # Batch to stay under URL limit. Use smaller batches when both
    # elements and data_points are present.
    el_list = elements or []
    dp_list = data_points or []
    if len(el_list) > _MAX_BATCH_ELEMENTS:
        raise ValueError(
            f"Too many element identifiers ({len(el_list)}). "
            f"Maximum allowed is {_MAX_BATCH_ELEMENTS}."
        )
    if len(dp_list) > _MAX_BATCH_DATA_POINTS:
        raise ValueError(
            f"Too many data points ({len(dp_list)}). "
            f"Maximum allowed is {_MAX_BATCH_DATA_POINTS}."
        )
    has_both = bool(el_list and dp_list)
    elem_batch_size = (
        _ELEM_BATCH_SIZE_WITH_DATA_POINTS if has_both else _ELEM_BATCH_SIZE
    )
    dp_batch_size = _DP_BATCH_SIZE_WITH_ELEMENTS if has_both else _DP_BATCH_SIZE

    def _batches_under_limit() -> list[tuple[list[str] | None, list[str] | None]]:
        """Return (el_batch, dp_batch) pairs for batching."""
        if not elem_batches and not dp_batches:
            return []
        e_batches = (
            cast(list[list[str] | None], elem_batches) if elem_batches else [None]
        )
        d_batches = cast(list[list[str] | None], dp_batches) if dp_batches else [None]
        return [(eb, db) for eb in e_batches for db in d_batches]

    elem_batches: list[list[str]] = []
    dp_batches: list[list[str]] = []
    for i in range(0, len(el_list), elem_batch_size):
        elem_batches.append(el_list[i : i + elem_batch_size])
    for i in range(0, len(dp_list), dp_batch_size):
        dp_batches.append(dp_list[i : i + dp_batch_size])

    # Sub-split any batch that still exceeds limit
    def _ensure_fits(
        *,
        batches: list[tuple[list[str] | None, list[str] | None]],
    ) -> list[tuple[list[str] | None, list[str] | None]]:
        out: list[tuple[list[str] | None, list[str] | None]] = []
        for el_b, dp_b in batches:
            p = _params_with(el=el_b, dp=dp_b)
            if _estimate_query_url_length(url=url, params=p) <= _MAX_QUERY_URL_LENGTH:
                out.append((el_b, dp_b))
            elif el_b and len(el_b) > 1:
                # Split elements in half
                mid = len(el_b) // 2
                out.extend(
                    _ensure_fits(batches=[(el_b[:mid], dp_b), (el_b[mid:], dp_b)])
                )
            elif dp_b and len(dp_b) > 1:
                # Split data_points in half
                mid = len(dp_b) // 2
                out.extend(
                    _ensure_fits(batches=[(el_b, dp_b[:mid]), (el_b, dp_b[mid:])])
                )
            else:
                # Single item still too long - skip or raise
                raise ValueError(
                    "PTP query params too large (URL length limit). "
                    "Try fewer elements or data_points."
                )
        return out

    all_batches = _batches_under_limit()
    if not all_batches:
        raise ValueError(
            "PTP query params too large (URL length limit). "
            "Try fewer elements or data_points."
        )
    if len(all_batches) > _MAX_BATCH_REQUESTS:
        raise ValueError(
            "PTP query would require too many batched requests. "
            "Try fewer elements or data_points."
        )
    final_batches = _ensure_fits(batches=all_batches)
    if len(final_batches) > _MAX_BATCH_REQUESTS:
        raise ValueError(
            "PTP query would require too many batched requests. "
            "Try fewer elements or data_points."
        )

    responses: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for el_batch, dp_batch in final_batches:
            p = _params_with(
                el=el_batch or None,
                dp=dp_batch or None,
            )
            resp = await _fetch_ptp_query(
                client=client,
                url=url,
                headers=headers,
                params=p,
                logger=logger,
            )
            responses.append(resp)

    return _merge_ptp_data_responses(responses=responses)


async def explore_ptp_api_route(*, token_manager: TokenManager) -> dict[str, Any]:
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
