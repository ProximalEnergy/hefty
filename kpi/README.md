## Field Naming Guidlines

```
[Device Axis] + [Quantity] + (Unit) + (time axis)
```

The entire name should be snake case.

1.  **Device Axis**
    Describes the device axis of the particular data array. The name should match
    the naming from `core.enumerations.DeviceType` but should be lower case.
    If there is no device axis, the first term should be `project`.

2.  **Quantity**
    Flexible, brief, human readable description of the field. All lower case.

3.  **Unit**
    All lower case. Only needed if there is a unit.

4.  **Time Axis**
    Short version of the `base.enums.Time` enum. Only needed if there is a time axis.

Use `> build.log 2>&1` if you need to debug a failing terminal.

```
 . ./auth_aws_codeartifact.sh
 docker buildx build --platform linux/arm64 --provenance=false --build-arg UV_INDEX_PROXIMAL_PASSWORD=$UV_INDEX_PROXIMAL_PASSWORD -t kpi-pipeline-image:latest .
```

Test it locally

```
docker run --platform linux/arm64 -p 9000:8080 kpi-pipeline-image:latest
curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"date": "2025-12-10", "project_id": "3b63ea38-cf28-4880-810e-41a81209d640", "kpi_type_ids": [25]}'
```

create ecr

```
aws ecr create-repository --repository-name kpi-pipeline-ecr --region us-east-2
```

```
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 016997484973.dkr.ecr.us-east-2.amazonaws.com
docker tag kpi-pipeline-image:latest 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest
docker push 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest
aws lambda create-function --function-name kpi-pipeline-lambda --package-type Image --code ImageUri=016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest --architectures arm64 --role arn:aws:iam::016997484973:role/AWSLambda_ReadOnlyAccess_ECR
aws lambda update-function-code \
  --function-name kpi-pipeline-lambda \
  --image-uri 016997484973.dkr.ecr.us-east-2.amazonaws.com/kpi-pipeline-ecr:latest \
  --publish
```

test it

```
aws lambda invoke --function-name kpi-pipeline-lambda --payload '{"date": "2025-12-10", "project_id": "3b63ea38-cf28-4880-810e-41a81209d640", "kpi_type_ids": [25]}' --cli-binary-format raw-in-base64-out /dev/stdout
```
