import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SCRIPT_DIR = Path(__file__).resolve().parent
API_ROOT = SCRIPT_DIR.parent
REPO_ROOT = API_ROOT.parent
PVEEM_ROOT = REPO_ROOT / "pv-eem"

sys.path.append(str(API_ROOT))

from app._utils.aws import get_parameters_by_path  # noqa: E402

ENV_PATH = PVEEM_ROOT / ".env.from_parameter_store"
DEFAULT_PARAMETER_STORE_PATHS = [
    "/proximal/pv-eem/",
    "/proximal/pveem/",
]  # noqa: S105
API_PARAMETER_STORE_PATH = "/proximal/api/"  # noqa: S105
API_OVERRIDDEN_KEYS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
]
REGION_NAME = "us-east-2"
PERSONAL_ENV_VARS: list[str] = []


def _get_parameter_store_paths(*, override: str | None) -> list[str]:
    """Return parameter store paths for pv-eem env lookup.

    Args:
        override: Optional explicit path from
            ``PVEEM_PARAMETER_STORE_PATH``.

    Returns:
        Ordered list of paths to query in AWS SSM Parameter Store.
    """
    if override:
        return [override]
    return DEFAULT_PARAMETER_STORE_PATHS


def generate_env_file() -> None:
    """Generate pv-eem env values from AWS Parameter Store."""
    override_path = os.getenv("PVEEM_PARAMETER_STORE_PATH")
    parameters: dict[str, str] = {}
    last_error: Exception | None = None
    paths = _get_parameter_store_paths(override=override_path)

    for path in paths:
        try:
            parameters = get_parameters_by_path(
                path=path,
                region_name=REGION_NAME,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Failed retrieving parameters from %s: %s", path, exc)
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

    try:
        api_parameters = get_parameters_by_path(
            path=API_PARAMETER_STORE_PATH,
            region_name=REGION_NAME,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed retrieving required API parameters from %s: %s",
            API_PARAMETER_STORE_PATH,
            exc,
        )
        logger.error(
            "Please ensure API parameters are readable from %s",
            API_PARAMETER_STORE_PATH,
        )
        sys.exit(1)

    missing_api_keys: list[str] = []
    for key in API_OVERRIDDEN_KEYS:
        value = api_parameters.get(key)
        if value is None:
            missing_api_keys.append(key)
            continue
        parameters[key] = value

    if missing_api_keys:
        logger.error(
            "Missing required keys in %s: %s",
            API_PARAMETER_STORE_PATH,
            ", ".join(missing_api_keys),
        )
        sys.exit(1)

    with open(ENV_PATH, "w") as env_file:
        env_file.write(
            "# Environment variables from AWS Systems Manager Parameter Store\n"
            "# This file is generated at {}\n\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        if PERSONAL_ENV_VARS:
            env_file.write("# User-specific environment variables - set manually\n")
            env_file.writelines(f"{var}=\n" for var in PERSONAL_ENV_VARS)
            env_file.write("\n")

        env_file.write("# Secrets from AWS Systems Manager Parameter Store\n")
        for key in sorted(parameters):
            value = parameters[key]
            env_file.write(f'{key}="{value}"\n')


if __name__ == "__main__":
    generate_env_file()
