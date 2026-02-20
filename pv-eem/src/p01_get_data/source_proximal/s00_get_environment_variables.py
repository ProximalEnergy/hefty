import os

from dotenv import load_dotenv


def get_environment_variables() -> tuple[str, str, str, str, str]:
    """Loads the database uri from project .env file"""
    # Environment Variables
    load_dotenv()

    # QC on environment
    ENVIRONMENT: str | None = os.getenv("ENVIRONMENT")
    match ENVIRONMENT:
        case "DEV" | "STAGE" | "PROD" | "VALIDATE":
            pass
        case _:
            raise ValueError("ENVIRONMENT must be DEV, STAGE, PROD, or VALIDATE")

    # Switch on Environment
    DB_URI: str | None
    match ENVIRONMENT:
        case "PROD":
            DB_URI = os.getenv("DB_URI_PROD")
        case "DEV" | "STAGE" | "VALIDATE":
            DB_URI = os.getenv("DB_URI_DEV")
        case _:
            raise ValueError("DB_URI_PROD or DB_URI_DEV in .env file cannot be None")

    # Error handling
    match DB_URI:
        case None:
            raise ValueError("DB_URI_PROD or DB_URI_DEV in .env file cannot be None")
        case _:
            pass

    # QC on AWS Environment Variables
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    match AWS_ACCESS_KEY_ID:
        case None:
            raise ValueError("AWS_ACCESS_KEY_ID is missing from .env file")
        case _:
            pass

    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    match AWS_SECRET_ACCESS_KEY:
        case None:
            raise ValueError("AWS_SECRET_ACCESS_KEY is missing from .env file")
        case _:
            pass

    AWS_S3_BUCKET_NAME: str | None = os.getenv("AWS_S3_BUCKET_NAME")
    match AWS_S3_BUCKET_NAME:
        case None:
            raise ValueError("AWS_S3_BUCKET_NAME is missing from .env file")
        case _:
            pass

    return (
        ENVIRONMENT,
        DB_URI,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        AWS_S3_BUCKET_NAME,
    )
