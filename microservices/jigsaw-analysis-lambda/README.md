# jigsaw-analysis-lambda

Detects PV DC combiner GIS/SCADA tag mismatches using spatial correlation
analysis during cloudy, high-variability periods. The analysis date is treated
as the end of a 14-day lookback. The algorithm first ranks candidate windows
using 5-minute SQL buckets, then fetches high-resolution data only for the top
candidate windows before running swap detection.

Invoked by the API route
`/v1/protected/web-application/projects/{project_id}/combiner-correlation-analysis`
and the web-app **Detect Mismatches** button on the PV DC Combiner block page.

AWS Lambda function name: `jigsaw-analysis-docker`  
ECR repository: `jigsaw-lambda`

## Configuration

Set via AWS Secrets Manager secret `microservices/jigsaw_analysis` (recommended)
or legacy plain Lambda environment variables:

| Key | Description |
| --- | --- |
| `PROXIMAL_API_KEY` | Operational API key (`x-api-key`) |
| `CONNECTION_STRING` | Timescale/TSDB psycopg2 connection string |
| `PROXIMAL_BASE_URL` | Optional; defaults to `https://api.proximal.energy` |

Override secret name with `JIGSAW_ANALYSIS_SECRET_NAME`. For local Docker runs
with env vars only, set `JIGSAW_ANALYSIS_SKIP_SECRETS=1`.

## Deploy

From monorepo root (requires AWS credentials and ECR push access):

```bash
microservices/jigsaw-analysis-lambda/_scripts/deploy.sh
```

## Test locally

```bash
docker buildx build --platform linux/arm64 --provenance=false --load \
  -f microservices/jigsaw-analysis-lambda/Dockerfile \
  -t jigsaw-analysis:test .
```

```bash
docker run --rm --platform linux/arm64 -p 9000:8080 \
  -e AWS_REGION=us-east-2 \
  -e JIGSAW_ANALYSIS_SKIP_SECRETS=1 \
  -e PROXIMAL_API_KEY=... \
  -e CONNECTION_STRING=... \
  jigsaw-analysis:test
```

```bash
curl -s -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{
    "project_id": "<uuid>",
    "analysis_date": "2025-01-15",
    "block_names": ["BLOCK_01"]
  }'
```

## Event contract

```json
{
  "project_id": "uuid",
    "analysis_date": "YYYY-MM-DD",
  "block_names": ["optional", "block", "names"]
}
```

`analysis_date` is the local end date for a 14-day lookback. For example,
`2025-01-15` ranks candidate windows from `2025-01-02` through the end of
`2025-01-15`, then runs swap detection on selected high-resolution windows.

Response body (HTTP 200):

```json
{
  "BLOCK_01": {
    "swaps": [[12345, 12346]],
    "warnings": []
  }
}
```

`swaps` entries are pairs of **tag_id** integers.
