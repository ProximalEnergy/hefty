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


async def get_user_email_from_clerk(*, user_id: str, api_prod: bool) -> str | None:
    """Get user email from Clerk."""
    # Use the correct Clerk secret key based on environment
    clerk_secret_key = (
        settings.CLERK_SECRET_KEY if api_prod else settings.CLERK_SECRET_KEY_DEVELOPMENT
    )

    try:
        with Clerk(bearer_auth=clerk_secret_key) as clerk:
            clerk_user = clerk.users.get(user_id=user_id)
            if clerk_user and clerk_user.email_addresses:
                return str(clerk_user.email_addresses[0].email_address)
    except models.ClerkErrors:
        pass
    return None


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


async def send_drone_inspection_order_email(
    *,
    provider_email: str,
    user_email: str,
    user_name: str,
    company_name: str,
    project_name: str,
    timing: str,
) -> None:
    """Send a drone inspection order email to the provider.

    Args:
        provider_email (str): The email of the drone provider.
        user_email (str): The email of the user requesting the inspection.
        user_name (str): The name of the user.
        company_name (str): The name of the user's company.
        project_name (str): The name of the project.
        timing (str): The timing preference for the inspection.
    """
    import boto3

    ses_client = boto3.client("sesv2", region_name="us-east-2")

    subject = f"New Drone Inspection Request - {project_name}"

    html_body = f"""
    <html>
    <body>
        <p>Hello,</p>
        
        <p>I would like to request a new drone inspection for our site.</p>
        
        <p><strong>Customer:</strong> {company_name}</p>
        <p><strong>Site:</strong> {project_name}</p>
        <p><strong>Scope:</strong> Full site inspection</p>
        <p><strong>Inspection Type:</strong> Module Advanced</p>
        <p><strong>Timing:</strong> {timing}</p>
        
        <p>Please let me know your availability and next steps.</p>
        
        <p>Best regards,<br>
        {user_name}<br>
        {user_email}</p>
    </body>
    </html>
    """

    email_kwargs = {
        "FromEmailAddress": "orders@proximal.energy",
        "Destination": {
            "ToAddresses": [provider_email],
            "CcAddresses": [user_email, "orders@proximal.energy"],
        },
        "Content": {
            "Simple": {
                "Subject": {"Data": subject},
                "Body": {
                    "Html": {"Data": html_body},
                },
            },
        },
    }

    ses_client.send_email(**email_kwargs)
