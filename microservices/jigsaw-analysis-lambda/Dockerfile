# https://docs.astral.sh/uv/guides/integration/aws-lambda/
FROM ghcr.io/astral-sh/uv:0.10.0 AS uv

FROM public.ecr.aws/lambda/python:3.12-arm64 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_INSTALLER_METADATA=1
ENV UV_LINK_MODE=copy

WORKDIR /build

COPY uv.lock pyproject.toml ./
COPY core/pyproject.toml core/README.md ./core/
COPY core/src/ ./core/src/
COPY microservices/jigsaw-analysis-lambda/pyproject.toml \
  ./microservices/jigsaw-analysis-lambda/
COPY microservices/jigsaw-analysis-lambda/_scripts/install_lambda_dependencies.sh \
  ./microservices/jigsaw-analysis-lambda/_scripts/
COPY microservices/jigsaw-analysis-lambda/lambda_function.py \
  ./microservices/jigsaw-analysis-lambda/
COPY microservices/jigsaw-analysis-lambda/config.py \
  ./microservices/jigsaw-analysis-lambda/
COPY microservices/jigsaw-analysis-lambda/proximal_api.py \
  ./microservices/jigsaw-analysis-lambda/
COPY microservices/jigsaw-analysis-lambda/jigsaw.py \
  ./microservices/jigsaw-analysis-lambda/

RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    sh ./microservices/jigsaw-analysis-lambda/_scripts/install_lambda_dependencies.sh

FROM public.ecr.aws/lambda/python:3.12-arm64

COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}
COPY microservices/jigsaw-analysis-lambda/lambda_function.py ${LAMBDA_TASK_ROOT}
COPY microservices/jigsaw-analysis-lambda/config.py ${LAMBDA_TASK_ROOT}
COPY microservices/jigsaw-analysis-lambda/proximal_api.py ${LAMBDA_TASK_ROOT}
COPY microservices/jigsaw-analysis-lambda/jigsaw.py ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
