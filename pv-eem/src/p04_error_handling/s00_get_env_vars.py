import os

from dotenv import load_dotenv


def get_environment_variables() -> dict[str, str]:
    # Environment Variables
    """Run get_environment_variables."""
    load_dotenv()

    # QC on environment
    WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL")
    match WEBHOOK_URL:
        case str():
            pass
        case _:
            raise ValueError("WEBHOOK_URL must be a string")

    ENVIRONMENT: str | None = os.getenv("ENVIRONMENT")
    match ENVIRONMENT:
        case str():
            pass
        case _:
            raise ValueError("ENVIRONMENT must be a string")

    return {
        "WEBHOOK_URL": WEBHOOK_URL,
        "ENVIRONMENT": ENVIRONMENT,
    }
