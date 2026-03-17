from _utils.environment_variables import (
    EnvironmentVariables,
    load_environment_variables,
)


def get_environment_variables() -> EnvironmentVariables:
    """Load runtime environment variables from the project .env file."""
    env_vars = load_environment_variables()
    env_vars.require_environment()
    env_vars.require_database_url()
    env_vars.require_aws_s3_bucket_name()
    env_vars.require_clickhouse_credentials()
    return env_vars
