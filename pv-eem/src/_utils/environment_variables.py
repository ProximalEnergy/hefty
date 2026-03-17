import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class EnvironmentVariables:
    """Application environment variables loaded from the project .env file."""

    environment: str | None
    database_url: str | None
    aws_s3_bucket_name: str | None
    clickhouse_host: str | None
    clickhouse_user: str | None
    clickhouse_password: str | None
    webhook_url: str | None
    aws_lambda_function_name: str | None

    @property
    def is_aws_lambda(self) -> bool:
        """Whether the application is running inside AWS Lambda."""
        return self.aws_lambda_function_name is not None

    def require_environment(self) -> str:
        """Return a validated application environment name."""
        match self.environment:
            case "DEV" | "STAGE" | "PROD" | "VALIDATE":
                return self.environment
            case _:
                raise ValueError(
                    "ENVIRONMENT must be DEV, STAGE, PROD, or VALIDATE"
                )

    def require_database_url(self) -> str:
        """Return the database URL or raise if it is missing."""
        return _require_string(
            value=self.database_url,
            env_var_name="DATABASE_URL",
        )

    def require_aws_s3_bucket_name(self) -> str:
        """Return the S3 bucket name or raise if it is missing."""
        return _require_string(
            value=self.aws_s3_bucket_name,
            env_var_name="AWS_S3_BUCKET_NAME",
        )

    def require_clickhouse_credentials(self) -> tuple[str, str, str]:
        """Return ClickHouse credentials or raise if any value is missing."""
        return (
            _require_string(
                value=self.clickhouse_host,
                env_var_name="CLICKHOUSE_HOST",
            ),
            _require_string(
                value=self.clickhouse_user,
                env_var_name="CLICKHOUSE_USER",
            ),
            _require_string(
                value=self.clickhouse_password,
                env_var_name="CLICKHOUSE_PASSWORD",
            ),
        )

    def require_webhook_url(self) -> str:
        """Return the Google Chat webhook URL or raise if it is missing."""
        return _require_string(
            value=self.webhook_url,
            env_var_name="WEBHOOK_URL",
        )


def load_environment_variables() -> EnvironmentVariables:
    """Load application environment variables from the project .env file."""
    load_dotenv()

    return EnvironmentVariables(
        environment=os.getenv("ENVIRONMENT"),
        database_url=os.getenv("DATABASE_URL"),
        aws_s3_bucket_name=os.getenv("AWS_S3_BUCKET_NAME"),
        clickhouse_host=os.getenv("CLICKHOUSE_HOST"),
        clickhouse_user=os.getenv("CLICKHOUSE_USER"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD"),
        webhook_url=os.getenv("WEBHOOK_URL"),
        aws_lambda_function_name=os.getenv("AWS_LAMBDA_FUNCTION_NAME"),
    )


def _require_string(*, value: str | None, env_var_name: str) -> str:
    match value:
        case str():
            return value
        case _:
            raise ValueError(f"{env_var_name} is missing from .env file")
