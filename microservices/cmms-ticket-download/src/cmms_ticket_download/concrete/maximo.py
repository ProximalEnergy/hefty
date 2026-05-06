import math
import os
from datetime import datetime
from typing import Any, cast

import httpx
from dotenv import load_dotenv

from cmms_ticket_download.typed_classes import (
    CMMSSessionProtocol,
    CMMSTicketDownloadTicket,
)
from cmms_ticket_download.utils import ensure_200

# get url for tickets, relative to the base_url
MAXIMO_TICKET_PATH = ""
DATE_FORMAT = "%Y-%m-%d"


class MaximoSession(CMMSSessionProtocol):
    """Maximo CMMS API session."""

    def __init__(
        self,
        *,
        base_url: str,
        aws_secret_key: str,
        aws_secret_username: str = "",
    ):
        self.base_url = base_url
        self.aws_secret_username = aws_secret_username
        self.aws_secret_key = aws_secret_key

    def get_raw_tickets(
        self,
        *,
        client: httpx.Client,
        project_name: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[Any, Any]]:
        """Fetch Maximo work orders matching the CMMS project and date range.

        Args:
            client: HTTP client used for Maximo requests.
            project_name: Maximo OSLC where clause fragment for the project.
            start: Optional lower bound for report date.
            end: Optional upper bound for report date.
        """

        # authenticate
        client.headers.update({"MAXAUTH": self.aws_secret_key})
        tickets = []

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
            where_clauses.append(f'reportdate>="{start.strftime(DATE_FORMAT)}"')
        if end:
            where_clauses.append(f'reportdate<="{end.strftime(DATE_FORMAT)}"')

        params["oslc.where"] = " and ".join(where_clauses)

        total_count = self._get_response(client=client, params={**params, "count": 1})[
            "totalCount"
        ]
        total_pages = math.ceil(total_count / page_size)

        for page_number in range(1, total_pages + 1):
            params["pageno"] = page_number
            response = self._get_response(client=client, params=params)
            tickets.extend(response["rdfs:member"])

        return tickets

    def _get_response(
        self, *, client: httpx.Client, params: dict[Any, Any]
    ) -> dict[Any, Any]:
        response = client.get(self.base_url + MAXIMO_TICKET_PATH, params=params)
        ensure_200(response=response)
        return cast(dict[Any, Any], response.json())


def maximo_ticket_to_cmms_ticket(
    *, raw_ticket: dict[Any, Any], cmms_integration_id: int, base_url: str = ""
) -> CMMSTicketDownloadTicket:
    """Convert a Maximo work order payload to a normalized CMMS ticket.

    Args:
        raw_ticket: Maximo work order payload.
        cmms_integration_id: CMMS integration ID for the ticket.
        base_url: Provider base URL, unused for Maximo ticket links.
    """

    _unused_api_base_url = base_url
    return CMMSTicketDownloadTicket(
        cmms_integration_id=cmms_integration_id,
        source_id=raw_ticket["spi:workorderid"],
        key=raw_ticket["spi:wonum"],
        source_created_at=raw_ticket.get("spi:reportdate") or None,
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
        link=(
            "https://mcc.softwrench2.com/panel/work-order/sm/edit/"
            f"{raw_ticket.get('spi:workorderid')}"
        ),
        json_raw=raw_ticket,
    )


def fetch_maximo_tickets_debug():
    """Fetch Maximo tickets with local debug credentials."""

    project_name = 'location="DBD%"'
    base_url = "https://mccmaximo.softwrench2.com/maximo/oslc/os/mxwo"
    aws_secret_key = os.getenv("MAXIMO_API_KEY")
    maximo_session = MaximoSession(
        base_url=base_url,
        aws_secret_key=aws_secret_key,
    )
    with httpx.Client(timeout=30.0) as client:
        tickets = maximo_session.get_raw_tickets(
            client=client,
            project_name=project_name,
            start=datetime(2025, 4, 1),
            end=datetime(2025, 7, 31),
        )
    return tickets


if __name__ == "__main__":
    load_dotenv()
    fetch_maximo_tickets_debug()
