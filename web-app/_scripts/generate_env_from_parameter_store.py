import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SCRIPT_DIR = Path(__file__).resolve().parent
WEB_APP_ROOT = SCRIPT_DIR.parent
REPO_ROOT = WEB_APP_ROOT.parent

sys.path.append(str(REPO_ROOT / "api"))

from app._utils.aws import get_parameters_by_path  # noqa: E402

ENV_PATH = WEB_APP_ROOT / ".env.from_parameter_store"
DEFAULT_PARAMETER_STORE_PATHS = [
    "/proximal/web/",
    "/proximal/web-app/",
]  # noqa: S105
REGION_NAME = "us-east-2"
PERSONAL_ENV_VARS: list[str] = []


def _get_web_app_parameter_store_paths(*, override: str | None) -> list[str]:
    if override:
        return [override]
    return DEFAULT_PARAMETER_STORE_PATHS


def generate_web_app_env_file() -> None:
    """Handle generate env file."""
    override_path = os.getenv("WEB_APP_PARAMETER_STORE_PATH")
    parameters: dict[str, str] = {}
    last_error: Exception | None = None
    paths = _get_web_app_parameter_store_paths(override=override_path)

    for path in paths:
        try:
            parameters = get_parameters_by_path(
                path=path,
                region_name=REGION_NAME,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "Failed retrieving parameters from %s: %s",
                path,
                e,
            )
            continue

        if parameters:
            break

    if not parameters:
        logger.error(
            "No parameters found from AWS Parameter Store paths: %s",
            ", ".join(paths),
        )
        if last_error:
            logger.error("Last error: %s", last_error)
        logger.error(
            "Please ensure:\n"
            "1. AWS credentials are configured (aws configure)\n"
            "2. You have ssm:GetParametersByPath permission\n"
            "3. Parameters exist at the path(s) listed above"
        )
        sys.exit(1)

    with open(ENV_PATH, "w") as f:
        f.write(
            "# Environment variables from AWS Systems Manager Parameter Store\n"
            "# This file is generated at {}\n\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        if PERSONAL_ENV_VARS:
            f.write("# User-specific environment variables - set manually\n")
            f.writelines(f"{var}=\n" for var in PERSONAL_ENV_VARS)
            f.write("\n")

        f.write("# Secrets from AWS Systems Manager Parameter Store\n")
        for key in sorted(parameters):
            value = parameters[key]
            f.write(f'{key}="{value}"\n')


if __name__ == "__main__":
    generate_web_app_env_file()
