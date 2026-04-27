#!/usr/bin/env python3
"""Script to export all user emails from the database and Clerk.

This script:
1. Fetches all user_ids from the database
2. Gets email addresses from Clerk for each user
3. Exports to a text file with emails separated by commas (for BCC field)

Usage:
    python export_user_emails.py [--output output.txt] [--env production|development]

Requires:
    - DATABASE_URL environment variable or .env file
    - CLERK_SECRET_KEY or CLERK_SECRET_KEY_DEVELOPMENT environment variable
"""

import logging
import os
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_all_user_ids():
    """Get all user IDs from the database."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Parse connection string
    # Format: postgresql://user:password@host:port/database?sslmode=require
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM admin.users")
        user_ids = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found {len(user_ids)} users in database")
        return user_ids
    finally:
        cursor.close()
        conn.close()


def get_emails_from_clerk(user_ids: list[str], api_prod: bool) -> dict[str, str]:
    """Get email addresses from Clerk for given user IDs.

    Args:
        user_ids: List of Clerk user IDs
        api_prod: Whether to use production Clerk API

    Returns:
        Dictionary mapping user_id to email address
    """
    if api_prod:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
    else:
        clerk_secret_key = os.getenv("CLERK_SECRET_KEY_DEVELOPMENT")

    if not clerk_secret_key:
        raise ValueError(
            f"Clerk secret key not set for {'production' if api_prod else 'development'} environment"
        )

    user_emails = {}
    headers = {"Authorization": f"Bearer {clerk_secret_key}"}

    # Clerk API allows fetching users by ID
    # Process in batches to avoid rate limits
    batch_size = 100

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i : i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} users)...")

        for user_id in batch:
            try:
                response = requests.get(
                    f"https://api.clerk.com/v1/users/{user_id}",
                    headers=headers,
                    timeout=10,
                )

                if response.status_code == 200:
                    user_data = response.json()
                    email_addresses = user_data.get("email_addresses", [])
                    if email_addresses:
                        # Get primary email (first one or the one marked as primary)
                        primary_email_id = user_data.get("primary_email_address_id")
                        if primary_email_id:
                            email = next(
                                (
                                    e["email_address"]
                                    for e in email_addresses
                                    if e["id"] == primary_email_id
                                ),
                                email_addresses[0]["email_address"],
                            )
                        else:
                            email = email_addresses[0]["email_address"]
                        user_emails[user_id] = email
                        logger.debug(f"Found email for {user_id}: {email}")
                    else:
                        logger.warning(f"No email found for user {user_id}")
                elif response.status_code == 404:
                    logger.warning(f"User {user_id} not found in Clerk")
                else:
                    logger.warning(
                        f"Error fetching user {user_id}: {response.status_code} - {response.text}"
                    )
            except Exception as e:
                logger.warning(f"Unexpected error for user {user_id}: {e}")

    logger.info(f"Successfully fetched {len(user_emails)} email addresses")
    return user_emails


def export_user_emails(output_file: str = "user_emails.txt", api_prod: bool = True):
    """Export all user emails to a text file (comma-separated for BCC field).

    Args:
        output_file: Path to output text file
        api_prod: Whether to use production Clerk API
    """
    logger.info("Starting user email export...")

    # Get all user IDs from database
    user_ids = get_all_user_ids()

    if not user_ids:
        logger.warning("No users found in database")
        return

    # Get emails from Clerk
    user_emails = get_emails_from_clerk(user_ids, api_prod=api_prod)

    # Write to text file (comma-separated for easy BCC paste)
    output_path = Path(output_file)
    emails_list = [email for email in user_emails.values() if email]
    emails_text = ", ".join(emails_list)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(emails_text)

    logger.info(f"Exported {len(emails_list)} emails to {output_path}")
    logger.info(f"Found emails for {len(user_emails)} users")
    logger.info(f"Missing emails: {len(user_ids) - len(user_emails)}")
    logger.info(
        f"\nYou can copy the contents of {output_path} and paste into the BCC field of your email client."
    )


def export_user_emails_cli():
    """Run the email export CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export all user emails to text file (for BCC field)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="user_emails.txt",
        help="Output text file path (default: user_emails.txt)",
    )
    parser.add_argument(
        "--env",
        choices=["production", "development"],
        default="production",
        help="Environment to use (default: production)",
    )

    args = parser.parse_args()

    api_prod = args.env == "production"

    logger.info(f"Using {'production' if api_prod else 'development'} Clerk API")

    export_user_emails(output_file=args.output, api_prod=api_prod)


if __name__ == "__main__":
    export_user_emails_cli()
