# kpi-pipeline-fetcher

Lambda function that delegates work to the kpi-pipeline lambda

```
. ../../_scripts/auth_aws_codeartifact.sh
uv sync
docker buildx build \
  --platform linux/arm64 \
  --provenance=false \
  --build-arg \
  UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME=$UV_INDEX_PROXIMAL_PACKAGE_INDEX_USERNAME \
  --build-arg \
  UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD=$UV_INDEX_PROXIMAL_PACKAGE_INDEX_PASSWORD \
  -t kpi-pipeline-fetcher-image:latest .
docker run --platform linux/arm64 -p 9000:8080 kpi-pipeline-fetcher-image:latest
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"backfill_days": 1}'
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
aws ecr create-repository --repository-name kpi-pipeline-fetcher-ecr --region us-east-2
docker tag kpi-pipeline-fetcher-image:latest 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-fetcher-ecr:latest
docker push 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-fetcher-ecr:latest
aws lambda create-function --function-name kpi-pipeline-fetcher-lambda --package-type Image --code ImageUri=016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-fetcher-ecr:latest --architectures arm64 --role arn:aws:iam::016997484973:role/AWSLambda_ReadOnlyAccess_ECR
aws lambda update-function-code \
  --function-name kpi-pipeline-fetcher-lambda \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-fetcher-ecr:latest \
  --publish
aws lambda invoke --function-name kpi-pipeline-fetcher-lambda --payload '{"backfill_days": 1}' --cli-binary-format raw-in-base64-out /dev/stdout
```
