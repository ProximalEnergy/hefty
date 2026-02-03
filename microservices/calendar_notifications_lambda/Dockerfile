FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

# Build arguments for Code Artifact authentication and core version
ARG CODEARTIFACT_TOKEN
ARG AWS_REGION=us-east-2
ARG CORE_VERSION
# CORE_VERSION: If set, installs core from Code Artifact. If not set, copies source code.

# Copy Lambda handler (always needed)
COPY microservices/calendar_notifications_lambda/calendar_notifications_lambda.py ./calendar_notifications_lambda.py

# Install uv first
RUN pip install --no-cache-dir uv

# Install core package: either from Code Artifact (if CORE_VERSION is set) or copy source
RUN --mount=type=bind,source=core/src/core,target=/build-context/core,readonly \
    if [ -n "$CORE_VERSION" ]; then \
      # Install from Code Artifact with pinned version
      if [ -z "$CODEARTIFACT_TOKEN" ]; then \
        echo "ERROR: CODEARTIFACT_TOKEN is required when CORE_VERSION is set" && exit 1; \
      fi && \
      CODEARTIFACT_URL="https://aws:${CODEARTIFACT_TOKEN}@proximal-code-artifact-domain-016997484973.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/proximal-hub/simple/" && \
      uv pip install --system --no-cache \
        --index-url "$CODEARTIFACT_URL" \
        --extra-index-url "https://pypi.org/simple" \
        --index-strategy unsafe-best-match \
        "core==${CORE_VERSION}" && \
      echo "Installed core==${CORE_VERSION} from Code Artifact"; \
    else \
      # Copy core source code only if CodeArtifact is not being used
      cp -r /build-context/core ./core && \
      echo "CORE_VERSION not set, using copied source code from ./core"; \
    fi

# Install other dependencies
RUN uv pip install --system --no-cache \
      sqlalchemy \
      asyncpg \
      psycopg2-binary \
      geoalchemy2 \
      boto3 \
      botocore \
      python-dotenv \
      async-lru \
      clerk-backend-api \
      pydantic \
      typing-extensions \
      greenlet \
      jinja2 \
      python-dateutil \
      pandas \
      polars==1.35.2 \
      shapely \
      clickhouse-connect

CMD ["calendar_notifications_lambda.lambda_handler"]
