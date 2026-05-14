#!/bin/bash

set -euo pipefail

echo "Checking for core version bump..."

if ! command -v jq >/dev/null 2>&1; then
    echo "jq could not be found, please install it."
    exit 1
fi

current_version=$(
    uv run python - <<'EOF'
import tomllib

print(tomllib.load(open("core/pyproject.toml", "rb"))["project"]["version"])
EOF
)
echo "Current version in pyproject.toml: ${current_version}"

if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "AWS credentials not configured. Skipping version check."
    exit 0
fi

aws_output=$(
    aws codeartifact list-package-versions \
        --domain proximal-code-artifact-domain \
        --repository proximal-hub \
        --format pypi \
        --package core \
        --sort-by PUBLISHED_TIME 2>/dev/null || echo '{"versions":[]}'
)
latest_version=$(printf "%s" "$aws_output" | jq -r ".versions[0].version")
echo "Latest published version from CodeArtifact: ${latest_version}"

if [ -z "$latest_version" ] || [ "$latest_version" = "null" ]; then
    echo "Could not determine the latest version from CodeArtifact."
    echo "Assuming this is the first release."
    latest_version="0.0.0"
fi

(
    cd core || exit 1
    uv run python - <<EOF
from packaging.version import Version

current = "$current_version"
latest = "$latest_version"

current_release = Version(current).release
latest_release = Version(latest).release

if current_release <= latest_release:
    print(
        "::error::Version check failed. The current version "
        f"({current}) must be greater than the latest published version "
        f"({latest}). Please bump the version in core/pyproject.toml."
    )
    exit(1)

print(
    f"Version check passed. Current version ({current}) > "
    f"Latest version ({latest})."
)
EOF
)
