# Build stage
FROM public.ecr.aws/lambda/python:3.12 AS builder

ARG UV_INDEX_PROXIMAL_PASSWORD
ARG UV_INDEX_PROXIMAL_USERNAME

# Install uv
RUN pip install uv

# Copy your pyproject.toml file into the container
COPY pyproject.toml .

# copy src folder into the container
COPY src/ ./src/

# Install dependencies from pyproject.toml into the target directory
# Set environment variables during installation to ensure they're available
RUN uv pip install . --target /tmp/deps

# Runtime stage
FROM public.ecr.aws/lambda/python:3.12

# Copy dependencies from builder stage
COPY --from=builder /tmp/deps ${LAMBDA_TASK_ROOT}

# copy .env file into the container
COPY .env ${LAMBDA_TASK_ROOT}

# Copy the lambda function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the correct handler for the function
CMD ["lambda_function.lambda_handler"]