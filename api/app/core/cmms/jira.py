from collections.abc import Generator

import requests
from requests.auth import HTTPBasicAuth

from app.core.cmms.cmms import CMMSSession, CMMSTicket

##
# Implementation of the concrete CMMSSession class for Jira
#

# get url for tickets, relative to the base_url
JIRA_TICKET_PATH = "/search"


class JiraSession(CMMSSession):
    """Concrete implementation of CMMSSession for Jira CMMS provider.

    This class implements the abstract CMMSSession interface specifically for Jira's
    API. It handles authentication, ticket retrieval, and data normalization for
    Jira's specific API format.
    """

    def __init__(
        self,
        *,
        base_url: str,
        session: requests.Session | None = None,
    ):
        """Initialize a new Jira session.

        Args:
            base_url (str): Base URL for the Jira API
            session (Optional[requests.Session]): Existing requests session to use
        """
        super().__init__(base_url=base_url, session=session)

    def authenticate(self, *, username: str, api_key: str):
        """Authenticate with the Jira API using Basic Authentication.

        Sets up HTTP Basic Authentication using the provided username and API key.
        Also configures the session to accept JSON responses.

        Args:
            username (str): Jira username for authentication
            api_key (str): Jira API key for authentication
        """
        self.session.auth = HTTPBasicAuth(username, api_key)
        self.session.headers.update({"Accept": "application/json"})

    def to_cmms_ticket(
        self,
        *,
        raw_ticket: dict,
    ) -> CMMSTicket:
        """Convert raw Jira ticket data to a standardized CMMSTicket.

        Maps Jira-specific fields to the standardized CMMSTicket format.
        Required fields use direct dictionary access and will raise KeyError if missing.
        Optional fields use dict.get() and will return None if missing.

        Args:
            raw_ticket (dict): Raw ticket data from Jira's API

        Returns:
            CMMSTicket: Normalized ticket object

        Raises:
            KeyError: If a required field is missing from the raw ticket data
        """
        fields = raw_ticket["fields"]
        # required fields use the brackets [] and so throw a key error if they are not present
        # optional fields use the get method and so return None if they are not present
        return CMMSTicket(
            cmms_provider="Jira",
            id=raw_ticket["id"],
            key=raw_ticket["key"],
            created_at=fields.get("created"),
            due_date=fields.get("duedate"),
            summary=fields.get("summary"),
            status=fields.get("status", {}).get("name"),
            status_change_at=fields.get("statuscategorychangedate"),
            priority=fields.get("priority", {}).get("name"),
            reporter=fields.get("reporter", {}).get("displayName"),
            link=f"{self.base_url[:-11]}/browse/{raw_ticket['key']}",
        )

    def _generate_tickets_raw(
        self,
        *,
        project_name: str,
        start: str | None = None,
        end: str | None = None,
        device_ids: list | None = None,
    ) -> Generator[list[dict], None, None]:
        """Generate raw tickets from the Jira API.

        Creates a generator that yields batches of raw tickets from Jira's API,
        filtered by the provided parameters. Uses pagination to handle large result sets.

        Note: Device ID filtering is not supported in the Jira implementation.

        Args:
            project_name (str): Project name to filter tickets by (using custom field 11502)
            start (Optional[str]): Only show tickets created after this date/time
            end (Optional[str]): Only show tickets created before this date/time
            device_ids (Optional[List[int]]): Not supported in Jira implementation

        Yields:
            List[dict]: Batches of raw ticket data from Jira's API

        Raises:
            NotImplementedError: If device_ids parameter is provided
        """
        page_size = 50

        # todo: implement device filtering
        if device_ids is not None:
            # empty generator
            return
            yield

        # create the jql statement
        jql_statement = f'cf[11502] ~ "{project_name}"'
        if start is not None:
            jql_statement += f" & created >= '{start}'"
        if end is not None:
            jql_statement += f" & created <= '{end}'"

        params = {
            "jql": jql_statement,
            "maxResults": page_size,
            "startAt": 0,
        }

        first_response = self.get(
            url=self.base_url + JIRA_TICKET_PATH,
            params=params,
        )

        yield first_response["issues"]

        total_count = first_response["total"]

        if total_count > page_size:
            for start_idx in range(page_size, total_count, page_size):
                params["startAt"] = start_idx
                response = self.get(
                    url=self.base_url + JIRA_TICKET_PATH,
                    params=params,
                )
                yield response["issues"]
