import os

from dotenv import load_dotenv


def get_environment_variables() -> tuple[str, str, str]:
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

    aws_s3_bucket_name: str | None = os.getenv("AWS_S3_BUCKET_NAME")
    match aws_s3_bucket_name:
        case None:
            raise ValueError("AWS_S3_BUCKET_NAME is missing from .env file")
        case _:
            pass

    clickhouse_host: str | None = os.getenv("CLICKHOUSE_HOST")
    match clickhouse_host:
        case None:
            raise ValueError("CLICKHOUSE_HOST is missing from .env file")
        case _:
            pass

    clickhouse_user: str | None = os.getenv("CLICKHOUSE_USER")
    match clickhouse_user:
        case None:
            raise ValueError("CLICKHOUSE_USER is missing from .env file")
        case _:
            pass

    clickhouse_password: str | None = os.getenv("CLICKHOUSE_PASSWORD")
    match clickhouse_password:
        case None:
            raise ValueError("CLICKHOUSE_PASSWORD is missing from .env file")
        case _:
            pass

    return (
        environment,
        database_url,
        aws_s3_bucket_name,
    )
