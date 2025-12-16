import sys
from datetime import datetime
from pathlib import Path

from app.settings import logger

# Resolve path relative to the repository root (where this script is located)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# add repo root to sys.path so that we can import app._utils.aws
sys.path.append(str(REPO_ROOT))

from app._utils.aws import get_parameters_by_path  # noqa: E402

ENV_PATH = REPO_ROOT / ".env.from_parameter_store"
PARAMETER_STORE_PATH = "/proximal/api/"  # noqa: S105
REGION_NAME = "us-east-2"
PERSONAL_ENV_VARS = [
    "EXCEL_PATH",
    "apiKey",
]


def generate_env_file():
    """Handle generate env file."""
    try:
        parameters = get_parameters_by_path(
            path=PARAMETER_STORE_PATH,
            region_name=REGION_NAME,
        )
    except Exception as e:
        logger.error(
            f"""Error retrieving parameters from AWS Parameter Store: {e}
            \nPlease ensure:
            1. AWS credentials are configured (aws configure)
            2. You have ssm:GetParametersByPath permission
            3. Parameters exist at path: {PARAMETER_STORE_PATH}
            """
        )
        sys.exit(1)

    # write to .env.from_parameter_store
    with open(ENV_PATH, "w") as f:
        # header
        f.write(
            "# Environment variables from AWS Systems Manager Parameter Store\n"
            "# This file is generated at {}\n\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        # development environment
        f.write(
            '# Assuming development environment\nENVIRONMENT="development"\n\n',
        )

        # empty personal environment variables
        f.write("# User-specific environment variables - must be set manually\n")
        f.writelines(f"{var}=\n" for var in PERSONAL_ENV_VARS)
        f.write("\n")

        # secrets
        f.write("# Secrets from AWS Systems Manager Parameter Store\n")
        for key in sorted(parameters):
            value = parameters[key]
            f.write(f'{key}="{value}"\n')


if __name__ == "__main__":
    generate_env_file()
