import asyncio
from typing import Any

import httpx
from app._utils.aws import get_secret
from app.logger import logger


class ZeitviewAPI:
    BASE_URL = "https://helio-external-api.production.zeitview.com"

    def __init__(self, *, drone_integration_id: int):
        secret_name = f"drone_integrations/drone_integration_id/{drone_integration_id}"
        try:
            secret_dict = get_secret(secret_name=secret_name)
            if not secret_dict:
                raise ValueError(f"Secret is empty for {secret_name}")
            api_key = secret_dict.get("zeitview_api_key")
        except Exception as e:
            logger.error(f"Failed to get or parse secret '{secret_name}': {e}")
            raise ValueError(
                f"Could not retrieve or parse secret: {secret_name}"
            ) from e

        if not api_key:
            raise ValueError(f"'zeitview_api_key' not found in secret: {secret_name}")

        self.api_key = api_key
        self.headers = {"api-key": self.api_key, "Content-Type": "application/json"}

    async def _make_request(
        self,
        *,
        endpoint: str,
        method: str = "POST",
        json_data: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make a request to the Zeitview API with retry logic and rate limiting"""
        url = f"{self.BASE_URL}{endpoint}"
        logger.debug(f"Making request to: {url}")
        logger.debug(f"Request payload: {json_data}")

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, headers=self.headers, json=json_data, timeout=300
                    )
                if response.status_code != 200:
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response content: {response.text}")
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result
            except httpx.TimeoutException as e:
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{max_retries} for {url}: {e}"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 504:
                    logger.warning(
                        f"504 Gateway Timeout on attempt {attempt + 1}/{max_retries} for {url}"
                    )
                    if attempt == max_retries - 1:
                        raise
                    # Longer delay for 504 errors
                    await asyncio.sleep(5 * (2**attempt))
                else:
                    logger.error(
                        f"HTTP error on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2**attempt)
            except Exception as e:
                logger.error(
                    f"Unexpected error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        # This should never be reached, but just in case
        raise Exception("Max retries exceeded")

    async def query_sites(self, *, site_name: str | None = None) -> dict[str, Any]:
        """Query all sites or filter by site name"""
        payload: dict[str, Any] = {
            "fields": [
                "site_id",
                "site_capacity_mw",
            ],  # Only allowed fields according to API spec
            "filters": {},
        }
        if site_name:
            payload["filters"]["site_name"] = site_name

        return await self._make_request(endpoint="/sites/query", json_data=payload)

    async def query_site_by_uuid(self, *, site_uuid: str) -> dict[str, Any]:
        """Query a site by its UUID"""
        payload = {"fields": ["site_id", "site_capacity_mw", "site_name", "site_uuid"]}
        return await self._make_request(
            endpoint=f"/sites/{site_uuid}/query", json_data=payload
        )

    async def query_site_inspections(
        self, *, site_uuid: str, only_latest: bool = False
    ) -> dict[str, Any]:
        """Query all inspections for a specific site, handling pagination."""
        all_inspections = []
        page = 1
        page_size = 200  # Fetch 200 at a time to be more efficient

        base_payload = {
            "fields": [
                "report_summary",
                "grades",
                "observations",
                "total_power_loss_percent",
                "total_affected_modules",
                "site_id",
                "service_tier",
                "site_capacity_mw",
                "total_power_loss_kw",
            ],
            "filters": {"only_latest_inspections": only_latest},
            "page_size": page_size,
        }

        while True:
            payload = base_payload.copy()
            payload["page"] = page
            response_data = await self._make_request(
                endpoint=f"/sites/{site_uuid}/inspections/query", json_data=payload
            )

            inspections = response_data.get("data", [])
            all_inspections.extend(inspections)

            pagination = response_data.get("metadata", {}).get("pagination", {})
            next_page = pagination.get("next_page")

            if not next_page:
                break

            page = int(next_page)

        # The final dictionary should still contain the metadata from the last call,
        # but the data key will contain all inspections.
        final_response = response_data
        final_response["data"] = all_inspections
        return final_response

    async def query_inspection_anomalies(
        self, *, inspection_uuid: str, start_page: int = 1, page_callback=None
    ) -> dict[str, Any]:
        """
        Query all anomalies for a specific inspection, handling pagination.

        Args:
            inspection_uuid: The inspection UUID to query
            start_page: Page to start from (for resuming interrupted syncs)
            page_callback: Optional callback function called after each page with (page_data, page_number)
        """
        all_anomalies = []
        page = start_page
        page_size = 200  # Reduced page size to be more conservative

        while True:
            logger.info(f"Fetching page {page} for inspection {inspection_uuid}")
            payload = {"page": page, "page_size": page_size}
            response_data = await self._make_request(
                endpoint=f"/inspections/{inspection_uuid}/anomalies/query",
                json_data=payload,
            )

            anomalies = response_data.get("data", [])
            all_anomalies.extend(anomalies)

            # Call the callback function if provided
            if page_callback and callable(page_callback):
                await page_callback(anomalies, page)

            pagination = response_data.get("metadata", {}).get("pagination", {})
            next_page = pagination.get("next_page")

            if not next_page:
                break

            page = int(next_page)

            # Rate limiting: wait 1 second between requests to be respectful to Zeitview's API
            await asyncio.sleep(1)

        # The final dictionary should still contain the metadata from the last call,
        # but the data key will contain all anomalies.
        final_response = response_data
        final_response["data"] = all_anomalies
        return final_response
