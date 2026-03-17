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

WORKDIR /build

COPY pyproject.toml uv.lock ./
COPY _scripts/install_lambda_dependencies.sh _scripts/read_pyproject.py \
    ./_scripts/

# Bundle locked runtime dependencies into the Lambda task root.
#
# Omit local workspace packages (`--no-emit-workspace`), skip the pinned
# `core` package (`--no-emit-package core`), and omit dev deps (`--no-dev`).
# Export the remaining locked runtime deps first, then install the exact
# pinned `core==...` from CodeArtifact.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    sh ./_scripts/install_lambda_dependencies.sh

FROM public.ecr.aws/lambda/python:3.12-arm64

# --- Python ---
# Copy the runtime dependencies from the builder stage. Runtime wheels are
# bundled into `${LAMBDA_TASK_ROOT}` there, so no extra system packages are
# needed in the final image.
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the specific function code
COPY src ${LAMBDA_TASK_ROOT}
COPY pyproject.toml ${LAMBDA_TASK_ROOT}
COPY ./.env /tmp/pveem.env
RUN grep -E '^(ENVIRONMENT|DATABASE_URL|WEBHOOK_URL|AWS_S3_BUCKET_NAME|CLICKHOUSE_HOST|CLICKHOUSE_USER|CLICKHOUSE_PASSWORD)=' \
    /tmp/pveem.env > ${LAMBDA_TASK_ROOT}/.env \
    && rm /tmp/pveem.env

# --- Networking ---
# Expose port 8080
EXPOSE 8080

# Set the CMD to your handler
CMD ["main.lambda_handler"]
