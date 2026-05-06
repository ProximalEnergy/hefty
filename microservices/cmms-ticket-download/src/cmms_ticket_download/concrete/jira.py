import os
from datetime import datetime
from typing import Any, cast

import httpx
from dotenv import load_dotenv
from httpx import BasicAuth

from cmms_ticket_download.typed_classes import (
    CMMSSessionProtocol,
    CMMSTicketDownloadTicket,
)
from cmms_ticket_download.utils import ensure_200

# get url for tickets, relative to the base_url
JIRA_TICKET_PATH = "/search/jql"
DATE_FORMAT = "%Y-%m-%d"


class JiraSession(CMMSSessionProtocol):
    """Jira CMMS API session."""

    def __init__(self, *, base_url: str, aws_secret_username: str, aws_secret_key: str):
        self.base_url = base_url
        self.aws_secret_username = aws_secret_username
        self.aws_secret_key = aws_secret_key

    def _authenticate(self, *, client: httpx.Client) -> None:
        client.auth = BasicAuth(self.aws_secret_username, self.aws_secret_key)
        client.headers.update({"Accept": "application/json"})

    def get_raw_tickets(
        self,
        *,
        client: httpx.Client,
        project_name: str,
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[Any, Any]]:
        """Fetch Jira issues matching the CMMS project and date range.

        Args:
            client: HTTP client used for Jira requests.
            project_name: Jira project field value to filter issues by.
            start: Optional lower bound for issue creation date.
            end: Optional upper bound for issue creation date.
        """

        self._authenticate(client=client)
        tickets = []

        jql_statement = f'cf[11502] ~ "{project_name}"'
        if start is not None:
            jql_statement += f" & created >= '{start.strftime(DATE_FORMAT)}'"
        if end is not None:
            jql_statement += f" & created <= '{end.strftime(DATE_FORMAT)}'"

        params = {
            "jql": jql_statement,
            "nextPageToken": None,
            "fields": "*all",
        }

        is_last = False

        while not is_last:
            response = self._get_response(client=client, params=params)
            tickets.extend(response["issues"])
            params["nextPageToken"] = response.get("nextPageToken")
            is_last = response["isLast"]

        return tickets

    def _get_response(
        self, *, client: httpx.Client, params: dict[Any, Any]
    ) -> dict[Any, Any]:
        response = client.get(self.base_url + JIRA_TICKET_PATH, params=params)
        ensure_200(response=response)
        return cast(dict[Any, Any], response.json())


def jira_ticket_to_cmms_ticket(
    *, raw_ticket: dict[Any, Any], cmms_integration_id: int, base_url: str
) -> CMMSTicketDownloadTicket:
    """Convert a Jira issue payload to a normalized CMMS ticket.

    Args:
        raw_ticket: Jira issue payload.
        cmms_integration_id: CMMS integration ID for the ticket.
        base_url: Jira REST API base URL used to build ticket links.
    """

    fields = raw_ticket["fields"]
    # Required fields use brackets and raise key errors when missing.
    # Optional fields use get and return None when missing.
    return CMMSTicketDownloadTicket(
        cmms_integration_id=cmms_integration_id,
        source_id=raw_ticket["id"],
        key=raw_ticket["key"],
        source_created_at=fields.get("created"),
        due_date=fields.get("duedate"),
        summary=fields.get("summary"),
        status=fields.get("status", {}).get("name"),
        status_change_at=fields.get("statuscategorychangedate"),
        priority=fields.get("priority", {}).get("name"),
        reporter=fields.get("reporter", {}).get("displayName"),
        link=f"{base_url[:-11]}/browse/{raw_ticket['key']}",
        json_raw=raw_ticket,
    )


def fetch_jira_tickets_debug():
    """Fetch Jira tickets with local debug credentials."""

    project_name = "REX__1247KV_CONTINEN_20230829155641_s"
    base_url = "https://stemedge.atlassian.net/rest/api/3"
    aws_username = "assetmanagement@excelsiorcapital.com"
    aws_secret_key = os.getenv("JIRA_API_KEY")
    jira_session = JiraSession(
        base_url=base_url,
        aws_secret_username=aws_username,
        aws_secret_key=aws_secret_key,
    )
    with httpx.Client(timeout=30.0) as client:
        tickets = jira_session.get_raw_tickets(
            client=client,
            project_name=project_name,
            start=datetime(2025, 4, 1),
            end=datetime(2025, 7, 31),
        )
    return tickets


if __name__ == "__main__":
    load_dotenv()
    fetch_jira_tickets_debug()
