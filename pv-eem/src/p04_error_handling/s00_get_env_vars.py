from _utils.environment_variables import (
    EnvironmentVariables,
    load_environment_variables,
)


def get_environment_variables() -> EnvironmentVariables:
    """Run get_environment_variables."""
    env_vars = load_environment_variables()
    env_vars.require_environment()
    env_vars.require_webhook_url()
    return env_vars
