import logging
import random
import string

from clerk_backend_api import Clerk, models
from core.utils.email_delivery import send_simple_email

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


async def create_clerk_user_util(*, user: UserCreate, company_name_short: str):
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
    html_body = (
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
    )
    await send_simple_email(
        from_address="support@proximal.energy",
        to=[email],
        subject="New Proximal User",
        html_body=html_body,
        bcc=["hunter@proximal.energy"],
    )


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
    await send_simple_email(
        from_address="orders@proximal.energy",
        to=[provider_email],
        subject=subject,
        html_body=html_body,
        cc=[user_email, "orders@proximal.energy"],
    )


async def get_clerk_user_metadata(*, user_id: str, clerk_secret_key: str) -> dict:
    """Fetch Clerk public metadata for a user.

    Args:
        user_id: Clerk user identifier to fetch.
        clerk_secret_key: Clerk API secret key for authentication.
    """
    try:
        with Clerk(
            bearer_auth=clerk_secret_key,
        ) as clerk:
            clerk_user = clerk.users.get(user_id=user_id)
            if not clerk_user:
                raise ValueError("User not found")
            return clerk_user.public_metadata or {}
    except models.ClerkErrors as e:
        return {"error": f"Failed to get user metadata: {e.data.errors[0].message}"}


async def get_clerk_user_image_url(*, user_id: str) -> str | None:
    """Get a user's profile picture URL from Clerk.

    Tries the primary Clerk instance first (based on ENVIRONMENT setting), then
    falls back to the other instance if the user is not found. This handles
    cases where users might exist in different Clerk instances (dev vs prod).

    Args:
        user_id (str): The ID of the user to get the image URL for.

    Returns:
        str | None: The user's profile picture URL, or None if not available.
    """
    # Determine which Clerk instance to use based on ENVIRONMENT setting
    # This is more reliable than api_prod which checks request headers
    environment = settings.ENVIRONMENT
    is_production = environment == "production"

    # Try primary Clerk instance first (based on ENVIRONMENT)
    clerk_secret_key = (
        settings.CLERK_SECRET_KEY
        if is_production
        else settings.CLERK_SECRET_KEY_DEVELOPMENT
    )

    try:
        with Clerk(bearer_auth=clerk_secret_key) as clerk:
            clerk_user = clerk.users.get(user_id=user_id)
            if clerk_user and hasattr(clerk_user, "image_url") and clerk_user.image_url:
                return str(clerk_user.image_url)
    except models.ClerkErrors as e:
        # If user not found, try the other Clerk instance as fallback
        error_message = str(e)
        if (
            "not found" in error_message.lower()
            or "resource_not_found" in error_message.lower()
        ):
            # Try the other Clerk instance (silently - this is expected behavior)
            fallback_secret_key = (
                settings.CLERK_SECRET_KEY_DEVELOPMENT
                if is_production
                else settings.CLERK_SECRET_KEY
            )
            try:
                with Clerk(bearer_auth=fallback_secret_key) as clerk:
                    clerk_user = clerk.users.get(user_id=user_id)
                    if (
                        clerk_user
                        and hasattr(clerk_user, "image_url")
                        and clerk_user.image_url
                    ):
                        return str(clerk_user.image_url)
            except Exception:
                # If fallback also fails, log and return None
                logging.warning(
                    "Failed to get Clerk user image URL for user "
                    f"{user_id} in both instances",
                )
        else:
            # Log other errors (not "not found" errors since we handle those
            # with fallback)
            logging.warning(
                f"Failed to get Clerk user image URL for user {user_id}: {e}",
            )
    except Exception as e:
        logging.warning(
            f"Unexpected error getting Clerk user image URL for user {user_id}: {e}",
        )
    return None


async def update_clerk_user_theme(*, user_id: str, theme: str, vite_environment: str):
    """Update a user's theme in Clerk while preserving existing metadata.

    Args:
        user_id (str): The ID of the user to update.
        theme (str): The theme to update the user to.
        vite_environment (str): The environment to use.
    """
    return await _update_clerk_public_metadata(
        user_id=user_id,
        metadata_updates={"parent_company": theme},
        vite_environment=vite_environment,
    )


async def update_clerk_user_demo_mode(
    *, user_id: str, demo_mode: bool, vite_environment: str
):
    """Toggle a user's demo mode in Clerk while preserving existing metadata.

    For superadmins on localhost/staging, their user account may exist in the
    production Clerk instance rather than the development instance. This function
    will try the primary Clerk instance first (based on vite_environment), then
    fall back to the other instance if the user is not found.

    Args:
        user_id (str): The ID of the user to update.
        demo_mode (bool): Set to True to enable demo mode, False to disable.
        vite_environment (str): The environment to use.
    """
    return await _update_clerk_public_metadata(
        user_id=user_id,
        metadata_updates={"demo": demo_mode},
        vite_environment=vite_environment,
    )


async def _update_clerk_public_metadata(
    *, user_id: str, metadata_updates: dict, vite_environment: str
) -> dict:
    """Update Clerk public metadata with fallback between Clerk instances.

    Args:
        user_id: The ID of the user to update.
        metadata_updates: Public metadata fields to update.
        vite_environment: The environment to use.

    Returns:
        dict: Either {"success": True} or {"error": "error message"}.
    """
    if vite_environment in ["PRODUCTION", "DEMO"]:
        primary_key = settings.CLERK_SECRET_KEY
        fallback_key = settings.CLERK_SECRET_KEY_DEVELOPMENT
    elif vite_environment in ["STAGING", "DEV"]:
        primary_key = settings.CLERK_SECRET_KEY_DEVELOPMENT
        fallback_key = settings.CLERK_SECRET_KEY
    else:
        raise ValueError("Invalid Vite environment")

    if primary_key is None:
        raise ValueError("Clerk secret key is not set for this environment")

    result = await _try_update_clerk_public_metadata(
        user_id=user_id,
        metadata_updates=metadata_updates,
        clerk_secret_key=primary_key,
    )

    error_message = result.get("error", "").lower()
    if any(term in error_message for term in ["not found", "resource_not_found"]):
        if fallback_key is not None:
            logging.info(
                "User %s not found in primary Clerk instance, trying fallback",
                user_id,
            )
            result = await _try_update_clerk_public_metadata(
                user_id=user_id,
                metadata_updates=metadata_updates,
                clerk_secret_key=fallback_key,
            )

    return result


async def _try_update_clerk_public_metadata(
    *, user_id: str, metadata_updates: dict, clerk_secret_key: str
) -> dict:
    """Attempt to update metadata for a user in a specific Clerk instance.

    Args:
        user_id: The ID of the user to update.
        metadata_updates: Public metadata fields to update.
        clerk_secret_key: The Clerk API secret key to use.

    Returns:
        dict: Either {"success": True} or {"error": "error message"}.
    """
    try:
        current_metadata = await get_clerk_user_metadata(
            user_id=user_id, clerk_secret_key=clerk_secret_key
        )
        if "error" in current_metadata:
            return current_metadata

        updated_metadata = {**current_metadata, **metadata_updates}

        with Clerk(
            bearer_auth=clerk_secret_key,
        ) as clerk:
            clerk_user = clerk.users.update(
                user_id=user_id,
                public_metadata=updated_metadata,
            )
            if not clerk_user:
                raise ValueError("Failed to update user")
        return {"success": True}
    except models.ClerkErrors as e:
        return {"error": f"Failed to update user: {e.data.errors[0].message}"}
