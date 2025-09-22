import math
from collections.abc import Generator

import requests

from app.core.cmms.cmms import CMMSSession, CMMSTicket

##
# Implementation of the concrete CMMSSession class for Maximo
#

# get url for tickets, relative to the base_url
# Currently, the path stored in the database is the full url.
# This may change depending on how we want to define base_url.
MAXIMO_TICKET_PATH = ""


class MaximoSession(CMMSSession):
    """Concrete implementation of CMMSSession for Maximo CMMS provider.

    This class implements the abstract CMMSSession interface specifically for Maximo's
    API. It handles authentication, ticket retrieval, and data normalization for
    Maximo's specific API format.
    """

    def __init__(
        self,
        *,
        base_url: str,
        session: requests.Session | None = None,
    ):
        """Initialize a new Maximo session.

        Args:
            base_url (str): Base URL for the Maximo API
            session (Optional[requests.Session]): Existing requests session to use
        """
        super().__init__(base_url=base_url, session=session)

    def authenticate(
        self,
        *,
        username: str,
        api_key: str,
    ):
        """Authenticate with the Maximo API using an API key.

        Note: Maximo only requires an API key for authentication, but the username
        parameter is required by the abstract class interface.

        Args:
            username (str): Not used in Maximo authentication
            api_key (str): API key for Maximo authentication
        """
        # no username is needed for Maximo authentication but it is required by the abstract class
        self.session.headers.update({"MAXAUTH": api_key})

    def get_ticket_count(
        self,
        *,
        params: dict,
    ) -> int:
        """Get the total count of tickets matching the given parameters.

        Args:
            params (dict): Query parameters for filtering tickets

        Returns:
            int: Total number of tickets matching the parameters
        """
        response = self.get(
            url=self.base_url + MAXIMO_TICKET_PATH,
            params={**params, "count": 1},
        )
        return response["totalCount"]

    def _generate_tickets_raw(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[dict], None, None]:
        """Generate raw tickets from the Maximo API.

        Creates a generator that yields batches of raw tickets from Maximo's API,
        filtered by the provided parameters. Uses pagination to handle large result sets.

        Args:
            project_name (str): Project name to filter tickets by
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List]): Filter tickets for these device IDs

        Yields:
            List[dict]: Batches of raw ticket data from Maximo's API
        """
        page_size = 50

        # create the params for the request
        params = {
            "oslc.select": "*, asset.description, location.description",
            "oslc.pageSize": page_size,
            "oslc.orderBy": "-reportdate",
            "_dropnulls": "0",
        }
        where_clauses = [project_name]
        if start:
            where_clauses.append(f'reportdate>="{start}"')
        if end:
            where_clauses.append(f'reportdate<="{end}"')
        if device_ids is not None:
            if len(device_ids) == 0:
                # empty generator
                return
                yield
            where_clauses.append(f'assetnum in ["{'","'.join(map(str, device_ids))}"]')

        params["oslc.where"] = " and ".join(where_clauses)

        total_count = self.get_ticket_count(params=params)
        total_pages = math.ceil(total_count / page_size)

        for page_number in range(1, total_pages + 1):
            params["pageno"] = page_number
            response = self.get(
                url=self.base_url + MAXIMO_TICKET_PATH,
                params=params,
            )
            yield response["rdfs:member"]

    def to_cmms_ticket(
        self,
        *,
        raw_ticket: dict,
    ) -> CMMSTicket:
        """Convert raw Maximo ticket data to a standardized CMMSTicket.

        Maps Maximo-specific fields to the standardized CMMSTicket format.
        Required fields use direct dictionary access and will raise KeyError if missing.
        Optional fields use dict.get() and will return None if missing.

        Args:
            raw_ticket (dict): Raw ticket data from Maximo's API

        Returns:
            CMMSTicket: Normalized ticket object

        Raises:
            KeyError: If a required field is missing from the raw ticket data
        """
        # required fields use the brackets [] and so throw a key error if they are not present
        # optional fields use the get method and so return None if they are not present
        # the `or None` pattern is meant to set to None if response is falsy (especially an empty string)
        return CMMSTicket(
            cmms_provider="Maximo",
            id=raw_ticket["spi:workorderid"],
            key=raw_ticket["spi:wonum"],
            created_at=raw_ticket.get("spi:reportdate") or None,
            summary=raw_ticket.get("spi:description"),
            summary_long=raw_ticket.get("spi:description_long"),
            status=raw_ticket.get("spi:status_description"),
            priority=raw_ticket.get("spi:tier_description"),
            reporter=raw_ticket.get("spi:reportedby"),
            assigned_to=raw_ticket.get("spi:owner"),
            location=raw_ticket.get("location", {}).get("description"),
            cmms_device_id=raw_ticket.get("spi:assetnum"),
            cmms_device_name=raw_ticket.get("asset", {}).get("description"),
            # todo: change the next link to be more general
            # issue: the baseu url doesn't match the ticket base url
            link=f"https://mcc.softwrench2.com/panel/work-order/sm/edit/{raw_ticket.get('spi:workorderid')}",
        )
