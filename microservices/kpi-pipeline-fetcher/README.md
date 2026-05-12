# kpi-pipeline-fetcher

Lambda function that delegates work to the kpi-pipeline lambda


## Image Creation


### Test Locally (optional)

```bash
 docker buildx build --platform linux/arm64 --provenance=false --load -f microservices/kpi-pipeline-fetcher/Dockerfile -t docker-image:test .
```

```bash
docker run --rm --platform linux/arm64 -p 9000:8080 \
    -e AWS_REGION=us-east-2 \
    -v "$HOME/.aws:/root/.aws:ro" \
    docker-image:test
```

In a separate terminal run

```bash
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"backfill_days": 3}'
```

Then kill the initial process.
