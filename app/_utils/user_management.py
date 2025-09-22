import random
import string

import boto3
from clerk_backend_api import Clerk, models

from app import settings
from app.interfaces import UserCreate


def generate_password(*, length: int = 16) -> str:
    """Generate a random password with the given length.

    Args:
        length (int, optional): The length of the password. Defaults to 16.

    Returns:
        str: The generated password.
    """
    characters = string.ascii_letters + string.digits
    password = "".join(random.choice(characters) for _ in range(length))

    return password


async def create_clerk_user(*, user: UserCreate, company_name_short: str):
    """Create a user in Clerk.

    Args:
        user (UserCreate): The user to create.
        company_name_short (str): The short name of the company.

    Returns:
        dict: A dictionary containing the password and user ID.
    """
    secure_password = generate_password()
    try:
        with Clerk(
            bearer_auth=settings.CLERK_SECRET_KEY,
        ) as clerk:
            clerk_user = clerk.users.create(
                email_address=[user.email],
                password=secure_password,
                first_name=user.first_name,
                last_name=user.last_name,
                public_metadata={
                    "parent_company": company_name_short,
                },
            )
            if not clerk_user:
                raise ValueError("Failed to create user")
        return {"password": secure_password, "user_id": clerk_user.id}
    except models.ClerkErrors as e:
        return {"error": f"Failed to create user: {e.data.errors[0].message}"}


async def delete_clerk_user(*, user_id: str):
    """Delete a user from Clerk.

    Args:
        user_id (str): The ID of the user to delete.

    Returns:
        dict: The deleted user.
    """

    with Clerk(
        bearer_auth=settings.CLERK_SECRET_KEY,
    ) as clerk:
        clerk_delete = clerk.users.delete(user_id=user_id)

    return clerk_delete


async def send_onboarding_email(*, email: str, name: str, password: str) -> None:
    """Send an onboarding email to a user.

    Args:
        email (str): The email of the user.
        name (str): The name of the user.
        password (str): The password of the user.
    """

    ses_client = boto3.client("sesv2", region_name="us-east-2")

    email_kwargs = {
        "FromEmailAddress": "support@proximal.energy",
        "Destination": {
            "ToAddresses": [email],
            "BccAddresses": ["hunter@proximal.energy"],
        },
        "Content": {
            "Simple": {
                "Subject": {"Data": "New Proximal User"},
                "Body": {
                    "Html": {
                        "Data": (
                            f"Hi {name},<br /><br />A new Proximal "
                            f"(https://app.proximal.energy) account has been created "
                            f"for you with the following credentials:<br /><br />"
                            f"Email: {email}<br />Password: <code>{password}</code>"
                            f"<br /><br />Please log in to configure your MFA code and "
                            f"feel free to update your password afterwards. "
                            f"<a href='https://docs.google.com/document/d/"
                            f"1xk6NhSWQEfrS1PTaon-MyvBnip6609dlyAGKXh_1WKo/edit?"
                            f"usp=sharing'>Check out the user onboarding document for "
                            f"additional details.</a><br /><br />Thanks,<br />"
                            f"The Proximal Team"
                        ),
                    },
                },
            },
        },
    }

    ses_client.send_email(**email_kwargs)
