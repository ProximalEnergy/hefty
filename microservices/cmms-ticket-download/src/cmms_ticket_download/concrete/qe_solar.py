from datetime import datetime
from typing import Any, cast

import httpx

from cmms_ticket_download.typed_classes import (
    CMMSSessionProtocol,
    CMMSTicketDownloadTicket,
)
from cmms_ticket_download.utils import ensure_200

# post url for authentication, relative to the base_url
QE_SOLAR_AUTH_PATH = "/auth/token"

# get url for tickets, relative to the base_url
QE_SOLAR_TICKET_PATH = "/v2/Tickets/customer/activity"

DATE_FORMAT = "%Y-%m-%d"


class QESolarSession(CMMSSessionProtocol):
    """QE Solar CMMS API session."""

    def __init__(
        self, *, base_url: str, aws_secret_key: str, aws_secret_username: str = ""
    ):
        self.base_url = base_url
        self.aws_secret_username = aws_secret_username
        self.aws_secret_key = aws_secret_key

    def _authenticate(self, *, client: httpx.Client) -> None:
        authentication_header = {"api_key": self.aws_secret_key}
        response = client.post(
            url=self.base_url + QE_SOLAR_AUTH_PATH,
            headers=authentication_header,
        )
        auth_token = response.json().get("auth_Token")
        if auth_token is None:
            raise Exception("Failed to get auth token")
        client.headers.update({"Authorization": f"Bearer {auth_token}"})

    def get_raw_tickets(
        self,
        *,
        client: httpx.Client,
        project_name: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[Any, Any]]:
        """Fetch QE Solar tickets matching the CMMS project and date range.

        Args:
            client: HTTP client used for QE Solar requests.
            project_name: QE Solar site name to filter tickets by.
            start: Optional lower bound for ticket open date.
            end: Optional upper bound for ticket open date.
        """

        if start is None:
            start_date = "2000-01-01"
        else:
            start_date = start.strftime(DATE_FORMAT)
        if end is None:
            end_date = "2100-01-01"
        else:
            end_date = end.strftime(DATE_FORMAT)

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "pageNumber": 1,
        }

        self._authenticate(client=client)

        first_response = self._get_response(client=client, params=params)

        # filter by project name because QE Solar doesn't natively support this
        tickets = [
            ticket
            for ticket in first_response["Tickets"]
            if ticket["SiteName"] == project_name
        ]

        if len(tickets) == 0:
            return tickets

        # total number of pages
        total_pages = int(first_response["Results"]["TotalPages"])

        # iterate over all pages, yielding tickets for the project
        for page in range(2, total_pages + 1):
            params["pageNumber"] = page
            response = self._get_response(client=client, params=params)
            new_tickets = [
                ticket
                for ticket in response["Tickets"]
                if ticket["SiteName"] == project_name
            ]
            tickets.extend(new_tickets)
        return tickets

    def _get_response(
        self, *, client: httpx.Client, params: dict[Any, Any]
    ) -> dict[Any, Any]:
        response = client.get(self.base_url + QE_SOLAR_TICKET_PATH, params=params)
        ensure_200(response=response)
        return cast(dict[Any, Any], response.json()[0])


def qe_solar_ticket_to_cmms_ticket(
    *, raw_ticket: dict[Any, Any], cmms_integration_id: int, base_url: str = ""
) -> CMMSTicketDownloadTicket:
    """Convert a QE Solar ticket payload to a normalized CMMS ticket.

    Args:
        raw_ticket: QE Solar ticket payload.
        cmms_integration_id: CMMS integration ID for the ticket.
        base_url: Provider base URL, unused for QE Solar ticket links.
    """

    _unused_api_base_url = base_url
    return CMMSTicketDownloadTicket(
        cmms_integration_id=cmms_integration_id,
        source_id=raw_ticket["Id"],
        key=raw_ticket["TicketNumber"],
        source_created_at=raw_ticket.get("TicketOpenDate"),
        summary=raw_ticket.get("Issue"),
        status=raw_ticket.get("Status"),
        priority=raw_ticket.get("Priority"),
        link=(
            "https://www.qesolartools.com/entities/ticket/detail/view/"
            f"{raw_ticket['TicketNumber']}"
        ),
        json_raw=raw_ticket,
    )
