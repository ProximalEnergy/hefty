# https://docs.astral.sh/uv/guides/integration/aws-lambda/
FROM ghcr.io/astral-sh/uv:0.10.0 AS uv

# -----------------
# Stage 1: Builder
# -----------------

# --- Bundle dependencies in the task root ---
FROM public.ecr.aws/lambda/python:3.12-arm64 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /build

# root level files
COPY uv.lock pyproject.toml ./
# files for core
COPY core/pyproject.toml core/README.md ./core/
COPY core/src/ ./core/src/
# files for microservices/kpi-pipeline-fetcher
COPY microservices/kpi-pipeline-fetcher/pyproject.toml ./microservices/kpi-pipeline-fetcher/
COPY microservices/kpi-pipeline-fetcher/_scripts/install_lambda_dependencies.sh ./microservices/kpi-pipeline-fetcher/_scripts/
COPY microservices/kpi-pipeline-fetcher/lambda_function.py ./microservices/kpi-pipeline-fetcher/

RUN --mount=from=uv,source=/uv,target=/bin/uv \
  --mount=type=cache,target=/root/.cache/uv \
  sh ./microservices/kpi-pipeline-fetcher/_scripts/install_lambda_dependencies.sh

# -----------------
# Stage 2: Runtime
# -----------------

FROM public.ecr.aws/lambda/python:3.12-arm64

# --- Python ---
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the lambda function code
COPY microservices/kpi-pipeline-fetcher/lambda_function.py ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
