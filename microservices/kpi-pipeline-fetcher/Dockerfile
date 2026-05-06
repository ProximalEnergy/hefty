# Build stage
FROM public.ecr.aws/lambda/python:3.12 AS builder

ARG UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME
ARG UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD

# Install uv
RUN pip install uv

# Copy your pyproject.toml file into the container
COPY pyproject.toml .

# Install dependencies from pyproject.toml into the target directory
# Set environment variables during installation to ensure they're available
RUN uv pip install . --target /tmp/deps

# Runtime stage
FROM public.ecr.aws/lambda/python:3.12

# Copy dependencies from builder stage
COPY --from=builder /tmp/deps ${LAMBDA_TASK_ROOT}

# Copy the lambda function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the correct handler for the function
CMD ["lambda_function.lambda_handler"]
