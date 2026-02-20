# Deployment Steps

## 1. Run tests locally
- `pytest`: run all tests
- `-s`: show print outputs
- `-k *`: run tests with filenames that match `*`
Run tests before deploying. There are no tests in CI/CD.

## [PROD]
### Github Actions
There is a workflow in `.github/workflows/deploy.yml`.
The general flow is:
- Trigger on a version tag pushed to a commit.
  - GitHub Actions normalizes tag names from `.` to `-` for image tags.
- Verify the tag version matches `pyproject.toml`.
- Build a Docker image from that commit and push it to ECR.
- Deploy CDK in `events/`, including Lambda `pv-eem` and EventBridge rules.


### Docker
- The docker image is tagged with the git tag name and latest.
- ECR stores image history so older versions can be deployed again.
- It is recommended to test with docker compose before PROD deploys.
- Docker is required because src plus dependencies is too large for ZIP Lambdas.

### Docker Gotchas
- Some packages are not available in the base Docker image.
- These are noted in `Dockerfile` comments.


### AWS Gotchas
- AWS blocks updates when a stack is in `ROLLBACK_COMPLETE`.
- Delete the failed CloudFormation stack before redeploying.

## [Stage]
### CDK
- `mise run pveem:cdk-deploy`
- Optionally pass an image tag:
  `mise run pveem:cdk-deploy -- -c imageTag=v0-16-6`

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
