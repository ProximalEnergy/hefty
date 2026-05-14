#!/bin/bash

set -euo pipefail

is_aws_credentials_missing() {
    local error_message="$1"
    local match_result

    shopt -s nocasematch
    if [[ "$error_message" == *"Unable to locate credentials"* ]]; then
        match_result=0
    else
        match_result=1
    fi
    shopt -u nocasematch

    return "$match_result"
}

is_codeartifact_package_not_found() {
    local error_message="$1"
    local match_result

    shopt -s nocasematch
    if [[ "$error_message" == *"ResourceNotFoundException"* ]] &&
        [[ "$error_message" == *"package"* ]]; then
        match_result=0
    else
        match_result=1
    fi
    shopt -u nocasematch

    return "$match_result"
}

echo "Checking for core version bump..."

current_version=$(
    uv run python - <<'EOF'
import tomllib

print(tomllib.load(open("core/pyproject.toml", "rb"))["project"]["version"])
EOF
)
echo "Current version in pyproject.toml: ${current_version}"

aws_error_file="$(mktemp)"
trap 'rm -f "$aws_error_file"' EXIT

if ! aws sts get-caller-identity >/dev/null 2>"$aws_error_file"; then
    aws_error="$(<"$aws_error_file")"
    if is_aws_credentials_missing "$aws_error"; then
        echo "AWS credentials not configured. Skipping version check."
        exit 0
    fi

    echo "Error: Failed to validate AWS credentials." >&2
    if [ -n "$aws_error" ]; then
        printf '%s\n' "$aws_error" >&2
    fi
    exit 1
fi

if latest_version=$(
    aws codeartifact list-package-versions \
        --domain proximal-code-artifact-domain \
        --repository proximal-hub \
        --format pypi \
        --package core \
        --no-paginate \
        --query defaultDisplayVersion \
        --output text 2>"$aws_error_file"
); then
    :
else
    latest_version_error="$(<"$aws_error_file")"
    if is_codeartifact_package_not_found "$latest_version_error"; then
        echo "Core package not found in CodeArtifact."
        echo "Assuming this is the first release."
        latest_version="0.0.0"
    else
        echo "Error: Failed to query latest core version from CodeArtifact."
        if [ -n "$latest_version_error" ]; then
            printf '%s\n' "$latest_version_error" >&2
        fi
        exit 1
    fi
fi

if [ -z "$latest_version" ] || [ "$latest_version" = "None" ]; then
    echo "Could not determine the latest version from CodeArtifact."
    echo "Assuming this is the first release."
    latest_version="0.0.0"
fi
echo "Latest published version from CodeArtifact: ${latest_version}"

(
    cd core || exit 1
    CURRENT_CORE_VERSION="$current_version" \
        LATEST_CORE_VERSION="$latest_version" \
        uv run python - <<'EOF'
import os

from packaging.version import Version

current = os.environ["CURRENT_CORE_VERSION"]
latest = os.environ["LATEST_CORE_VERSION"]

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
