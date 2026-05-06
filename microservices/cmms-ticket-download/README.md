# cmms-ticket-download

Runs on a schedule to pull ticket information from different CMMS providers and put it into our database.

## Building the Docker Image

Run this from the monorepo root so uv can see the workspace metadata.

```
> docker buildx build \
    --platform linux/arm64 \
    --provenance=false \
    -f microservices/cmms-ticket-download/Dockerfile \
    -t docker-image:latest \
    .
```

To test locally do

```
> docker run --platform linux/arm64 -e AWS_ACCESS_KEY_ID="<aws-access-key-id>" -e AWS_SECRET_ACCESS_KEY="aws-secret-access-key" -e AWS_DEFAULT_REGION="us-east-2" -p 9000:8080 docker-image:latest
```

Then in another shell

```
> curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"cmms_integration_id": 3, "start": "2025-05-01", "end": "2025-08-01"}'
```
