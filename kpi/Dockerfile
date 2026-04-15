# Build stage
FROM public.ecr.aws/lambda/python:3.12 AS builder

# Install uv
RUN pip install uv

# Copy local package sources from the monorepo root context.
WORKDIR /build
COPY core/pyproject.toml ./core/pyproject.toml
COPY core/README.md ./core/README.md
COPY core/src/ ./core/src/
COPY kpi/pyproject.toml ./kpi/pyproject.toml
COPY kpi/src/ ./kpi/src/

# Install dependencies from pyproject.toml into the target directory
WORKDIR /build/kpi
RUN uv pip install . --target /tmp/deps

# Runtime stage
FROM public.ecr.aws/lambda/python:3.12

# Copy dependencies from builder stage
COPY --from=builder /tmp/deps ${LAMBDA_TASK_ROOT}
COPY --from=builder /build/core/src/core ${LAMBDA_TASK_ROOT}/core

# copy .env file into the container
COPY kpi/.env ${LAMBDA_TASK_ROOT}

# Copy the lambda function code
COPY kpi/lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the correct handler for the function
CMD ["lambda_function.lambda_handler"]