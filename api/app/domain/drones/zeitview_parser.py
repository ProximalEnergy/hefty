import asyncio
from typing import Any

import httpx
from app._utils.aws import get_secret
from app.logger import logger


class ZeitviewAPI:
    """todo"""

    BASE_URL = "https://helio-external-api.production.zeitview.com"

    def __init__(
        self, *, drone_integration_id: int | None = None, api_key: str | None = None
    ):
        """todo

        Args:
            drone_integration_id: TODO: describe.
            api_key: TODO: describe.
        """
        if api_key:
            self.api_key = api_key
        elif drone_integration_id:
            secret_name = (
                f"drone_integrations/drone_integration_id/{drone_integration_id}"
            )
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
                raise ValueError(
                    f"'zeitview_api_key' not found in secret: {secret_name}"
                )
            self.api_key = api_key
        else:
            raise ValueError("Either drone_integration_id or api_key must be provided")

        self.headers = {"api-key": self.api_key, "Content-Type": "application/json"}

    @classmethod
    def from_api_key(cls, *, api_key: str):
        """Create a ZeitviewAPI instance using a direct API key.

        Args:
            api_key: TODO: describe.
        """
        return cls(api_key=api_key)

    async def _make_request(
        self,
        *,
        endpoint: str,
        method: str = "POST",
        json_data: dict | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Make a request to the Zeitview API with retry logic and rate limiting

        Args:
            endpoint: TODO: describe.
            method: TODO: describe.
            json_data: TODO: describe.
            max_retries: TODO: describe.
        """
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
                    logger.error(f"Request payload was: {json_data}")
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
                elif e.response.status_code == 422:
                    # 422 Unprocessable Entity - don't retry, raise immediately with details
                    error_detail = e.response.text
                    logger.error(
                        f"422 Validation error on {url}: {error_detail}. "
                        f"Request payload: {json_data}"
                    )
                    raise ValueError(f"API validation error: {error_detail}") from e
                else:
                    logger.error(
                        f"HTTP error on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                    logger.error(f"Response content: {e.response.text}")
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
        """Query all sites or filter by site name

        Args:
            site_name: TODO: describe.
        """
        # According to API spec, only certain fields are allowed in query endpoint
        # We'll query with minimal fields first, then enrich with individual queries
        payload: dict[str, Any] = {
            "fields": [
                "site_id",
                "site_capacity_mw",
            ],
            "filters": {},
            "page_size": 200,
        }
        if site_name:
            payload["filters"]["site_name"] = site_name

        sites_response = await self._make_request(
            endpoint="/sites/query", json_data=payload
        )

        # Enrich each site with site_name and site_uuid by querying individually
        # Note: This requires that we can query by site_id or that site_uuid
        # is returned in the initial response
        sites_data = sites_response.get("data", [])
        enriched_sites = []
        for site in sites_data:
            site_id = site.get("site_id")
            # Try to get site_uuid from the response first
            # If not available, we'll need to handle it differently
            # For now, assume the API might return it even if not in fields
            enriched_sites.append(site)

        sites_response["data"] = enriched_sites
        return sites_response

    async def query_site_by_uuid(self, *, site_uuid: str) -> dict[str, Any]:
        """Query a site by its UUID

        Args:
            site_uuid: TODO: describe.
        """
        payload = {"fields": ["site_id", "site_capacity_mw", "site_name", "site_uuid"]}
        return await self._make_request(
            endpoint=f"/sites/{site_uuid}/query", json_data=payload
        )

    async def query_site_inspections(
        self, *, site_uuid: str, only_latest: bool = False
    ) -> dict[str, Any]:
        """Query all inspections for a specific site, handling pagination.

        Args:
            site_uuid: TODO: describe.
            only_latest: TODO: describe.
        """
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
            page_callback: Optional callback function called after each page
                with (page_data, page_number)
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
