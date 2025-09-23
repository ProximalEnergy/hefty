# Use Python 3.12 slim image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/opt/uv-cache/

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies (without the project itself for better caching)
RUN --mount=type=cache,target=/opt/uv-cache/ \
    uv sync --locked --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN --mount=type=cache,target=/opt/uv-cache/ \
    uv sync --locked

# Expose port
EXPOSE 8000

# Set the PATH to include the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Command to run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "0"]
