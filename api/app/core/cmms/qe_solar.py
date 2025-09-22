from collections.abc import Generator

import requests

from app.core.cmms.cmms import CMMSSession, CMMSTicket
from app.utils import ensure_200

##
# Implementation of the concrete CMMSSession class for QE Solar
#

# post url for authentication, relative to the base_url
QE_SOLAR_AUTH_PATH = "/auth/token"

# get url for tickets, relative to the base_url
QE_SOLAR_TICKET_PATH = "/v2/Tickets/customer/activity"


class QESolarSession(CMMSSession):
    """Concrete implementation of CMMSSession for QE Solar CMMS provider.

    This class implements the abstract CMMSSession interface specifically for QE Solar's
    API. It handles authentication, ticket retrieval, and data normalization for
    QE Solar's specific API format.
    """

    def __init__(
        self,
        *,
        base_url: str,
        session: requests.Session | None = None,
    ):
        """Initialize a new QE Solar session.

        Args:
            base_url (str): Base URL for the QE Solar API
            session (Optional[requests.Session]): Existing requests session to use
        """
        super().__init__(base_url=base_url, session=session)

    def authenticate(
        self,
        *,
        username: str,
        api_key: str,
    ):
        """Authenticate with the QE Solar API using an API key.

        Note: QE Solar only requires an API key for authentication, but the username
        parameter is required by the abstract class interface. The authentication
        process involves a POST request to get a Bearer token.

        Args:
            username (str): Not used in QE Solar authentication
            api_key (str): API key for QE Solar authentication

        Raises:
            Exception: If authentication fails to retrieve a token
        """
        # no username is needed for QE Solar authentication but it is required by the abstract class

        # the QE Solar authentication first requires a post request to the auth/token endpoint
        authentication_header = {"api_key": api_key}
        response = ensure_200(
            response=self.session.post(
                url=self.base_url + QE_SOLAR_AUTH_PATH,
                headers=authentication_header,
            ),
        ).json()
        auth_token = response.get("auth_Token")
        if auth_token is None:
            raise Exception("Failed to get auth token")
        self.session.headers.update({"Authorization": f"Bearer {auth_token}"})

    def to_cmms_ticket(
        self,
        *,
        raw_ticket: dict,
    ) -> CMMSTicket:
        """Convert raw QE Solar ticket data to a standardized CMMSTicket.

        Maps QE Solar-specific fields to the standardized CMMSTicket format.
        Required fields use direct dictionary access and will raise KeyError if missing.
        Optional fields use dict.get() and will return None if missing.

        Args:
            raw_ticket (dict): Raw ticket data from QE Solar's API

        Returns:
            CMMSTicket: Normalized ticket object

        Raises:
            KeyError: If a required field is missing from the raw ticket data
        """
        # required fields use the brackets [] and so throw a key error if they are not present
        # optional fields use the get method and so return None if they are not present
        return CMMSTicket(
            cmms_provider="QE Solar",
            id=raw_ticket["Id"],
            key=raw_ticket["TicketNumber"],
            created_at=raw_ticket.get("TicketOpenDate"),
            summary=raw_ticket.get("Issue"),
            status=raw_ticket.get("Status"),
            priority=raw_ticket.get("Priority"),
            link=f"https://www.qesolartools.com/entities/ticket/detail/view/{raw_ticket['TicketNumber']}",
        )

    def _generate_tickets_raw(
        self,
        *,
        project_name: str,  # according to the CMMS provider
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[dict], None, None]:
        """Generate raw tickets from the QE Solar API.

        Creates a generator that yields batches of raw tickets from QE Solar's API,
        filtered by the provided parameters. Uses pagination to handle large result sets.
        Project name filtering is done client-side since QE Solar doesn't support it natively.

        Note: Device ID filtering is not supported in the QE Solar implementation.

        Args:
            project_name (str): Project name to filter tickets by (using SiteName field)
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List[int]]): Not supported in QE Solar implementation

        Yields:
            List[dict]: Batches of raw ticket data from QE Solar's API

        Raises:
            NotImplementedError: If device_ids parameter is provided
        """
        if start is None:
            start = "2000-01-01"
        if end is None:
            end = "2100-01-01"

        params = {
            "startDate": start,
            "endDate": end,
            "pageNumber": 1,
        }

        if device_ids is not None:
            # empty generator
            return
            yield

        # initial page of tickets, grabbing page metadata
        first_response = self.get(
            url=self.base_url + QE_SOLAR_TICKET_PATH,
            params=params,
        )[0]

        # filter by project name because QE Solar doesn't natively support this
        first_tickets = [
            ticket
            for ticket in first_response["Tickets"]
            if ticket["SiteName"] == project_name
        ]

        yield first_tickets

        # total number of pages
        total_pages = int(first_response["Results"]["TotalPages"])

        # iterate over all pages, yielding tickets for the project
        for page in range(2, total_pages + 1):
            params["pageNumber"] = page
            response = self.get(
                url=self.base_url + QE_SOLAR_TICKET_PATH,
                params=params,
            )[0]
            tickets = [
                ticket
                for ticket in response["Tickets"]
                if ticket["SiteName"] == project_name
            ]
            yield tickets
