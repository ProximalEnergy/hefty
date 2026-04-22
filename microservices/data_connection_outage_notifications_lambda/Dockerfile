FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

ARG CODEARTIFACT_TOKEN
ARG AWS_REGION=us-east-2
ARG CORE_VERSION

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /build/workspace/
COPY core /build/core
COPY microservices/data_connection_outage_notifications_lambda \
  /build/microservices/data_connection_outage_notifications_lambda

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
      uv pip install --system --no-cache \
        --no-sources-package core \
        /build/microservices/data_connection_outage_notifications_lambda && \
      echo \
        "Installed data_connection_outage_notifications_lambda against core==${CORE_VERSION}"; \
    else \
      constraints_file="/tmp/root-constraints.txt" && \
      uv export --project /build/workspace --frozen --no-dev --no-editable \
        --no-emit-workspace --no-hashes -o "$constraints_file" && \
      uv pip install --system --no-cache \
        -c "$constraints_file" \
        /build/microservices/data_connection_outage_notifications_lambda && \
      rm -f "$constraints_file" && \
      echo \
        "Installed data_connection_outage_notifications_lambda from local" \
        "project metadata using root uv.lock"; \
    fi && \
    rm -rf /build/workspace /build/core \
      /build/microservices/data_connection_outage_notifications_lambda

CMD ["data_connection_outage_notifications_lambda.lambda_handler"]
