import os

from dotenv import load_dotenv


def get_environment_variables() -> tuple[str, str, str, str, str]:
    """Load runtime environment variables from the project .env file."""
    # Environment Variables
    load_dotenv()

    # QC on environment
    environment: str | None = os.getenv("ENVIRONMENT")
    match environment:
        case "DEV" | "STAGE" | "PROD" | "VALIDATE":
            pass
        case _:
            raise ValueError("ENVIRONMENT must be DEV, STAGE, PROD, or VALIDATE")

    database_url: str | None = os.getenv("DATABASE_URL")
    match database_url:
        case None:
            raise ValueError("DATABASE_URL is missing from .env file")
        case _:
            pass

    # QC on AWS Environment Variables
    aws_access_key_id: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    match aws_access_key_id:
        case None:
            raise ValueError("AWS_ACCESS_KEY_ID is missing from .env file")
        case _:
            pass

    aws_secret_access_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    match aws_secret_access_key:
        case None:
            raise ValueError("AWS_SECRET_ACCESS_KEY is missing from .env file")
        case _:
            pass

    aws_s3_bucket_name: str | None = os.getenv("AWS_S3_BUCKET_NAME")
    match aws_s3_bucket_name:
        case None:
            raise ValueError("AWS_S3_BUCKET_NAME is missing from .env file")
        case _:
            pass

    return (
        environment,
        database_url,
        aws_access_key_id,
        aws_secret_access_key,
        aws_s3_bucket_name,
    )
