# Install ``core`` from the monorepo via ``uv pip install /build/core`` (deps from
# core/pyproject.toml). Root .dockerignore has ``!core/pyproject.toml`` and
# ``!core/README.md`` so those files are in the context for this COPY.
FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

ARG CODEARTIFACT_TOKEN
ARG AWS_REGION=us-east-2
ARG CORE_VERSION

COPY microservices/data_connection_outage_notifications_lambda/data_connection_outage_notifications_lambda.py ./data_connection_outage_notifications_lambda.py

RUN pip install --no-cache-dir uv

COPY core /build/core

RUN if [ -n "$CORE_VERSION" ]; then \
      if [ -z "$CODEARTIFACT_TOKEN" ]; then \
        echo "ERROR: CODEARTIFACT_TOKEN is required when CORE_VERSION is set" \
          && exit 1; \
      fi && \
      CODEARTIFACT_URL="https://aws:${CODEARTIFACT_TOKEN}@proximal-code-artifact-domain-016997484973.d.codeartifact.${AWS_REGION}.amazonaws.com/pypi/proximal-hub/simple/" && \
      uv pip install --system --no-cache \
        --index-url "$CODEARTIFACT_URL" \
        --extra-index-url "https://pypi.org/simple" \
        --index-strategy unsafe-best-match \
        "core==${CORE_VERSION}" && \
      rm -rf /build/core && \
      echo "Installed core==${CORE_VERSION} from Code Artifact"; \
    else \
      uv pip install --system --no-cache /build/core && \
      rm -rf /build/core && \
      echo "Installed core from monorepo source"; \
    fi

CMD ["data_connection_outage_notifications_lambda.lambda_handler"]
