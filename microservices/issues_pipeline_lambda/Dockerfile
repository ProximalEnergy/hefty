FROM public.ecr.aws/lambda/python:3.12-arm64

WORKDIR /var/task

RUN pip install --no-cache-dir uv

COPY core /build/core
COPY issues /build/issues

RUN rm -rf \
      /build/core/build \
      /build/core/dist \
      /build/core/*.egg-info \
      /build/core/src/*.egg-info \
      /build/issues/build \
      /build/issues/dist \
      /build/issues/*.egg-info && \
    mkdir -p /tmp/wheels && \
    cd /build/core && uv build --wheel --out-dir /tmp/wheels && \
    cd /build/issues && uv build --wheel --no-sources --out-dir /tmp/wheels && \
    uv pip install --system --no-cache --find-links /tmp/wheels \
      /tmp/wheels/core-*.whl && \
    uv pip install --system --no-cache --find-links /tmp/wheels \
      /tmp/wheels/issues-*.whl && \
    echo "Installed issues pipeline from freshly built local wheels" && \
    rm -rf /build/core /build/issues /tmp/wheels

CMD ["issues.lambda_handler.lambda_handler"]
