FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /build/workspace/
COPY core /build/workspace/core
COPY microservices/data_connection_outage_notifications_lambda \
  /build/workspace/microservices/data_connection_outage_notifications_lambda

RUN constraints_file="/tmp/root-constraints.txt" && \
  uv export --project /build/workspace --frozen --no-dev --no-editable \
    --no-emit-workspace --no-hashes -o "$constraints_file" && \
  uv pip install --system --no-cache \
    -c "$constraints_file" \
    -r "$constraints_file" && \
  uv pip install --system --no-cache --no-deps /build/workspace/core && \
  uv pip install --system --no-cache --no-deps \
    /build/workspace/microservices/data_connection_outage_notifications_lambda && \
  rm -f "$constraints_file" && \
  rm -rf /build/workspace

CMD ["data_connection_outage_notifications_lambda.lambda_handler"]
