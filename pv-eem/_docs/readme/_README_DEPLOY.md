# Deployment Steps

## 1. Run tests locally
- `pytest`: run all tests
- `-s`: show print outputs
- `-k *`: run tests with filenames that match `*`
Run tests before deploying. There are no tests in CI/CD.

## Deploy
### Local flow
- Run `mise run pveem:push-image`.
- The script reads `pyproject.toml` and pushes the image to ECR with both
  `<version>` and `latest` tags.
- The Docker build validates the pinned `core==...` dependency in
  `pyproject.toml` and installs that exact version from AWS CodeArtifact.
- The script builds a single ARM64 image locally and then pushes plain tags to
  ECR so Lambda gets a compatible manifest.
- Run `mise run pveem:cdk-deploy`.
- Unless you override it, CDK deploys the same `<version>` tag from
  `pyproject.toml`.
- Run `mise run pveem:deploy` to do checks, image push, and CDK deploy in one
  command.
- If the deployed Lambda only exposes `latest`, `pveem:deploy` treats that as
  a one-time migration case and still publishes the semver tag.

### Docker
- Source `../_scripts/auth_aws_codeartifact.sh` before building or pushing.
- The docker image is tagged with the `pyproject.toml` version and latest.
- ECR stores image history so older versions can be deployed again.
- It is recommended to test with docker compose before deployment.
- Docker is required because src plus dependencies is too large for ZIP Lambdas.

### Docker Gotchas
- Some packages are not available in the base Docker image.
- These are noted in `Dockerfile` comments.


### AWS Gotchas
- AWS blocks updates when a stack is in `ROLLBACK_COMPLETE`.
- Delete the failed CloudFormation stack before redeploying.
- If Lambda says `The image manifest, config or layer media type ... is not
  supported`, repush the image with `mise run pveem:push-image` before
  redeploying.

### CDK
- `mise run pveem:cdk-deploy`
- Optionally pass an image tag:
  `mise run pveem:cdk-deploy -- -c imageTag=0.16.6`

## One-Time SAM Decommission
Run this after CDK Lambda `pv-eem` is deployed and stable.

1. Deploy CDK with a known release tag and confirm scheduled runs succeed.
2. Confirm EventBridge rules are targeting Lambda `pv-eem`.
3. Delete the old SAM stack:
   `aws cloudformation delete-stack --stack-name \
   pv-expected-energy-lambda-stack --region <aws-region>`
4. Wait for stack deletion:
   `aws cloudformation wait stack-delete-complete --stack-name \
   pv-expected-energy-lambda-stack --region <aws-region>`
5. If the legacy Lambda still exists, delete it:
   `aws lambda delete-function --function-name pv-simulation \
   --region <aws-region>`
