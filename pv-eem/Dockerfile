# https://docs.astral.sh/uv/guides/integration/aws-lambda/
FROM ghcr.io/astral-sh/uv:0.10.0 AS uv

# --- Bundle dependencies in the task root ---
FROM public.ecr.aws/lambda/python:3.12-arm64 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /build

COPY uv.lock pyproject.toml ./
COPY core/pyproject.toml core/README.md ./core/
COPY core/src/ ./core/src/
COPY pv-eem/pyproject.toml ./pv-eem/
COPY pv-eem/_scripts/install_lambda_dependencies.sh ./pv-eem/_scripts/

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    sh ./pv-eem/_scripts/install_lambda_dependencies.sh

FROM public.ecr.aws/lambda/python:3.12-arm64

# --- Python ---
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the specific function code
COPY pv-eem/src ${LAMBDA_TASK_ROOT}
COPY pv-eem/pyproject.toml ${LAMBDA_TASK_ROOT}
COPY pv-eem/.env /tmp/pveem.env
RUN grep -E '^(ENVIRONMENT|DATABASE_URL|WEBHOOK_URL|AWS_S3_BUCKET_NAME|CLICKHOUSE_HOST|CLICKHOUSE_USER|CLICKHOUSE_PASSWORD)=' \
    /tmp/pveem.env > ${LAMBDA_TASK_ROOT}/.env \
    && rm /tmp/pveem.env

# --- Networking ---
EXPOSE 8080

CMD ["main.lambda_handler"]
