"""User management utilities for core."""

import logging

from clerk_backend_api import Clerk, models
from core.settings import get_clerk_secret_key

logger = logging.getLogger(__name__)


async def get_user_email_from_clerk(*, user_id: str) -> str | None:
    """Get user email from Clerk.

    Args:
        user_id: User ID.

    Returns:
        User email or None if not found.
    """
    clerk_secret_key = get_clerk_secret_key()
    if not clerk_secret_key:
        logger.warning("Clerk secret key not set")
        return None

    try:
        with Clerk(bearer_auth=clerk_secret_key) as clerk:
            clerk_user = clerk.users.get(user_id=user_id)
            if clerk_user and clerk_user.email_addresses:
                return str(clerk_user.email_addresses[0].email_address)
    except models.ClerkErrors:
        pass
    except Exception as e:
        logger.warning(f"Error getting user email from Clerk: {e}")
    return None
