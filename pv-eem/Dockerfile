# https://docs.astral.sh/uv/guides/integration/aws-lambda/

FROM ghcr.io/astral-sh/uv:0.10.0 AS uv

# --- Bundle dependencies in the task root ---
FROM public.ecr.aws/lambda/python:3.12-arm64 AS builder

ARG CODEARTIFACT_TOKEN

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Bundle locked runtime dependencies into the Lambda task root.
#
# Omit local workspace packages (`--no-emit-workspace`), skip the pinned
# `core` package (`--no-emit-package core`), and omit dev deps (`--no-dev`).
# Export the remaining locked runtime deps first, then install the exact
# pinned `core==...` from CodeArtifact.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly \
    test -n "${CODEARTIFACT_TOKEN}" || \
      (echo "ERROR: CODEARTIFACT_TOKEN is required" && exit 1) && \
    core_version="$(
      python - <<'PY'
import re
import tomllib
from pathlib import Path

project = tomllib.load(Path("pyproject.toml").open("rb"))
dependencies = project["project"]["dependencies"]
core_specs = [dep for dep in dependencies if dep.startswith("core")]

if len(core_specs) != 1:
    raise SystemExit(
        f"Expected exactly one core dependency entry, found {len(core_specs)}."
    )

match = re.fullmatch(r"core==([A-Za-z0-9][A-Za-z0-9._+-]*)", core_specs[0])
if match is None:
    raise SystemExit(
        "core dependency must be pinned as core==x.y.z in pyproject.toml."
    )

print(match.group(1), end="")
PY
    )" && \
    codeartifact_url="$(
      python - <<'PY'
import tomllib
from pathlib import Path

project = tomllib.load(Path("pyproject.toml").open("rb"))
indexes = project.get("tool", {}).get("uv", {}).get("index", [])
matching_urls = [
    index["url"]
    for index in indexes
    if index.get("name") == "proximal-package-index"
]

if len(matching_urls) != 1:
    raise SystemExit(
        "Expected exactly one proximal-package-index entry in pyproject.toml."
    )

print(matching_urls[0], end="")
PY
    )" && \
    case "${codeartifact_url}" in \
      https://*) \
        codeartifact_url="https://aws:${CODEARTIFACT_TOKEN}@\
${codeartifact_url#https://}" ;; \
      *) \
        echo "ERROR: CodeArtifact index URL must start with https://" && \
        exit 1 ;; \
    esac && \
    uv export --frozen --no-emit-workspace --no-dev --no-editable \
      --no-emit-package core \
      -o /tmp/requirements.lock.txt && \
    uv pip install -r /tmp/requirements.lock.txt \
      --target "${LAMBDA_TASK_ROOT}" && \
    uv pip install \
      --index "${codeartifact_url}" \
      --no-deps \
      --no-sources \
      --target "${LAMBDA_TASK_ROOT}" \
      "core==${core_version}" && \
    rm -f /tmp/requirements.lock.txt

FROM public.ecr.aws/lambda/python:3.12-arm64

# --- Python ---
# Copy the runtime dependencies from the builder stage. Runtime wheels are
# bundled into `${LAMBDA_TASK_ROOT}` there, so no extra system packages are
# needed in the final image.
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the specific function code
COPY src ${LAMBDA_TASK_ROOT}
COPY pyproject.toml ${LAMBDA_TASK_ROOT}
COPY ./.env ${LAMBDA_TASK_ROOT}/.env

# --- Networking ---
# Expose port 8080
EXPOSE 8080

# Set the CMD to your handler
CMD ["main.lambda_handler"]
