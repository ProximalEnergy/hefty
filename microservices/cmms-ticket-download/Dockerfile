# Build stage
FROM public.ecr.aws/lambda/python:3.12 AS builder

WORKDIR /build/mono/microservices/cmms-ticket-download

# Install uv
RUN pip install uv

COPY microservices/cmms-ticket-download/docker-workspace.toml \
  /build/mono/pyproject.toml
COPY microservices/cmms-ticket-download/pyproject.toml .
COPY core/ /build/mono/core/

# copy src folder into the container
COPY microservices/cmms-ticket-download/src/ ./src/

# Install dependencies from pyproject.toml into the target directory
# Set environment variables during installation to ensure they're available
RUN uv pip install . --target /tmp/deps

# Runtime stage
FROM public.ecr.aws/lambda/python:3.12

# Copy dependencies from builder stage
COPY --from=builder /tmp/deps ${LAMBDA_TASK_ROOT}

# copy .env file into the container
COPY microservices/cmms-ticket-download/.env ${LAMBDA_TASK_ROOT}

# Copy the lambda function code
COPY microservices/cmms-ticket-download/lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the correct handler for the function
CMD ["lambda_function.lambda_handler"]
