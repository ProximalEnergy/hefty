#!/bin/sh

set -eu

if [ -z "${CODEARTIFACT_TOKEN:-}" ]; then
    echo "ERROR: CODEARTIFACT_TOKEN is required"
    exit 1
fi

lambda_task_root="${LAMBDA_TASK_ROOT:?LAMBDA_TASK_ROOT must be set}"
requirements_path="/tmp/requirements.lock.txt"

core_version="$(
    python3 ./_scripts/read_pyproject.py core-version
)"
codeartifact_url="$(
    python3 ./_scripts/read_pyproject.py package-index-url
)"

case "${codeartifact_url}" in
    https://*)
        codeartifact_url="https://aws:${CODEARTIFACT_TOKEN}@\
${codeartifact_url#https://}"
        ;;
    *)
        echo "ERROR: CodeArtifact index URL must start with https://"
        exit 1
        ;;
esac

uv export --frozen --no-emit-workspace --no-dev --no-editable \
    --no-emit-package core \
    -o "${requirements_path}"
uv pip install -r "${requirements_path}" --target "${lambda_task_root}"
uv pip install \
    --index "${codeartifact_url}" \
    --no-deps \
    --no-sources \
    --target "${lambda_task_root}" \
    "core==${core_version}"

rm -f "${requirements_path}"
