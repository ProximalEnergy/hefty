# https://docs.astral.sh/uv/guides/integration/aws-lambda/

FROM ghcr.io/astral-sh/uv:0.8.3 AS uv

# --- Bundle dependencies in the task root ---
FROM public.ecr.aws/lambda/python:3.11-arm64 as builder

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Bundle the dependencies into the Lambda task root via `uv pip install --target`.
#
# Omit any local packages (`--no-emit-workspace`) and development dependencies (`--no-dev`).
# This ensures that the Docker layer cache is only invalidated when the `pyproject.toml` or `uv.lock`
# files change, but remains robust to changes in the application code.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt && \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.11-arm64

# --- Postgres ---
# Install Python and development tools
# - python3-devel is needed for psycopg2
# - postgresql-devel is needed for psycopg2
# - gcc is needed for psycopg2
RUN yum update -y && \
    yum install -y python3-devel \
    postgresql-devel \
    gcc \
    || (yum clean all && yum install -y \
    python3-devel \
    postgresql-devel \
    gcc \
    )

# --- Python ---
# Copy the runtime dependencies from the builder stage.
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
