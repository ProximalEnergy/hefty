import logging
import os
import random
import string
from typing import Any, Literal, TypedDict

import requests

logging.basicConfig(level=logging.INFO)


class UserDict(TypedDict):
    """
    A dictionary representing a user in Clerk.
    """

    first_name: str
    last_name: str
    email: str
    # Currently only "parent_company" is supported by Proximal, but this can
    # be extended to other metadata keys.
    public_metadata: dict[Literal["parent_company"], str] | None


def create_user(*, user: UserDict) -> None:
    """Create a user in Clerk.

    Args:
        user: TODO: describe.
    """

    # Generate a random password
    password = "".join(random.choices(string.ascii_letters + string.digits, k=16))

    # Create user data
    json_data: dict[str, Any] = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email_address": [user["email"]],
        "password": password,
    }

    # Add public metadata if it exists
    public_metadata = user.get("public_metadata")
    if public_metadata:
        json_data["public_metadata"] = public_metadata

    # Create user
    response = requests.post(
        "https://api.clerk.com/v1/users",
        headers={
            "Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}",
            "Content-Type": "application/json",
        },
        json=json_data,
    )

    # Log the response information
    if response.ok:
        data = response.json()
        logging.info("==========")
        logging.info(f"{data['first_name']} {data['last_name']} created!")
        logging.info(f"User ID: {data['id']}")
        logging.info(f"Email: {data['email_addresses'][0]['email_address']}")
        logging.info(f"Password: {password}")
        logging.info("==========")
        logging.info("")
    else:
        logging.error("==========")
        logging.error(f"Error: {response.status_code} {response.text}")
        logging.error("==========")
        logging.error("")
        logging.info("==========")


if __name__ == "__main__":
    clerk_secret_key = os.environ["CLERK_SECRET_KEY"]
    if not clerk_secret_key:
        raise ValueError("CLERK_SECRET_KEY is not set")
    if not clerk_secret_key.startswith("sk_live_"):
        raise ValueError("CLERK_SECRET_KEY is not a production secret key")

    users: list[UserDict] = [
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "public_metadata": {"parent_company": "company_name"},
        },
    ]

    logging.info("You are creating the following users:")
    for user in users:
        logging.info(f"\t{user['first_name']} {user['last_name']} ({user['email']})")
    response = input("Do you want to continue? (y/n): ")
    if response != "y":
        exit()

    for user in users:
        create_user(user=user)

    logging.info("DO NOT CLEAR TERMINAL BEFORE GETTING PASSWORDS!")
