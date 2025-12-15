import logging
import os

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
LINEAR_TEAM_ID = "1806ad3d-8d48-45ca-a6ef-4f33acf3c793"
UNKNOWN_COMPANY_ID = "d9c5181c-d59f-4c11-a763-a87a95096414"
CUSTOMER_FEEDBACK_LABEL_ID = "a853e6d3-085f-4069-872b-c48ada6b5485"


async def get_company_id_by_email(*, client, email: str) -> str | None:
    """todo

    Args:
        client: TODO: describe.
        email: TODO: describe.
    """
    try:
        domain = email.split("@")[1]
    except IndexError:
        return None

    query = gql(
        """
        query GetCustomers {
          customers {
            nodes {
              id
              domains
            }
          }
        }
        """
    )
    try:
        result = await client.execute(query)
        if result["customers"]["nodes"]:
            # Filter in Python to find matching domain
            for customer in result["customers"]["nodes"]:
                if customer.get("domains") and domain in customer["domains"]:
                    return str(customer["id"])
        return None
    except Exception as e:
        logging.warning(f"Error querying for company ID: {e}")
        return None


async def create_linear_issue(
    *,
    title: str,
    description: str,
    user_email: str,
    url: str | None = None,
    screenshot_data_uri: str | None = None,
):
    """todo

    Args:
        title: TODO: describe.
        description: TODO: describe.
        user_email: TODO: describe.
        url: TODO: describe.
        screenshot_data_uri: TODO: describe.
    """
    transport = AIOHTTPTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": f"{LINEAR_API_KEY}"},
    )

    async with Client(transport=transport, fetch_schema_from_transport=True) as session:
        customer_id = await get_company_id_by_email(
            client=session,
            email=user_email,
        )
        if not customer_id:
            customer_id = UNKNOWN_COMPANY_ID

        # Build full description with URL and screenshot if available
        full_description = description
        if url:
            full_description = (
                f"{full_description}\n\n🔗 [Link](https://app.proximal.energy{url})"
            )
        full_description = f"{full_description}\n\nSubmitted by {user_email}"
        if screenshot_data_uri:
            full_description = (
                f"{full_description}\n\n![screenshot]({screenshot_data_uri})"
            )

        mutation_str = """
            mutation CreateIssue(
                $title: String!,
                $description: String!,
                $teamId: String!,
                $labelIds: [String!]
            ) {
              issueCreate(
                input: {
                  title: $title
                  description: $description
                  teamId: $teamId
                  labelIds: $labelIds
                }
              ) {
                success
                issue {
                  id
                  title
                }
              }
            }
        """
        mutation = gql(mutation_str)
        params = {
            "title": title,
            "description": full_description,
            "teamId": LINEAR_TEAM_ID,
            "labelIds": [CUSTOMER_FEEDBACK_LABEL_ID],
        }
        try:
            issue_result = await session.execute(mutation, variable_values=params)

            # Only try to link customer if we have a valid UUID
            if (
                issue_result
                and issue_result.get("issueCreate", {}).get("success")
                and customer_id != UNKNOWN_COMPANY_ID
            ):
                issue_id = issue_result["issueCreate"]["issue"]["id"]

                # Create customer need to link issue to customer
                need_mutation = gql(
                    """
                    mutation CreateCustomerNeed(
                        $customerId: String!,
                        $issueId: String!
                    ) {
                      customerNeedCreate(
                        input: {
                          customerId: $customerId
                          issueId: $issueId
                        }
                      ) {
                        success
                      }
                    }
                    """
                )
                need_params = {
                    "customerId": customer_id,
                    "issueId": issue_id,
                }
                try:
                    await session.execute(need_mutation, variable_values=need_params)
                except Exception as e:
                    logging.warning(f"Error linking customer to issue: {e}")

            if issue_result and issue_result.get("issueCreate", {}).get("success"):
                return issue_result["issueCreate"]["issue"]["id"]
            return None
        except Exception as e:
            logging.warning(f"Error creating Linear issue: {e}")
            return None
