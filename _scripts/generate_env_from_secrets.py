import sys
from datetime import datetime
from pathlib import Path

# Resolve path relative to the repository root (where this script is located)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

# add repo root to sys.path so that we can import app._utils.aws
sys.path.append(str(REPO_ROOT))

from app._utils.aws import get_secret

ENV_PATH = REPO_ROOT / ".env.from_secrets"
AWS_SECRET_NAME = "api/env"  # noqa: S105
REGION_NAME = "us-east-2"
PERSONAL_ENV_VARS = [
    "EXCEL_PATH",
    "apiKey",
]


def generate_env_file():
    secret = get_secret(secret_name=AWS_SECRET_NAME, region_name=REGION_NAME)
    # write to .env.from_secrets
    with open(ENV_PATH, "w") as f:
        # header
        f.write(
            "# Environment variables from AWS Secrets Manager\n"
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
        f.write("# Secrets from AWS Secrets Manager\n")
        f.writelines(f'{key}="{value}"\n' for key, value in secret.items())


if __name__ == "__main__":
    generate_env_file()
