# cmms-ticket-download

Runs on a schedule to pull ticket information from different CMMS providers and put it into our database.

## Building the Docker Image

### Test Locally (optional)

```bash
 docker buildx build --platform linux/arm64 --provenance=false --load -f microservices/cmms-ticket-download/Dockerfile -t docker-image:test .
```

```bash
docker run --rm --platform linux/arm64 -p 9000:8080 \
    -e AWS_REGION=us-east-2 \
    -v "$HOME/.aws:/root/.aws:ro" \
    docker-image:test
```

In a separate terminal run

```bash
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"cmms_integration_id": 3, "start": "2025-05-01", "end": "2025-06-01"}'
```

Then kill the initial process.