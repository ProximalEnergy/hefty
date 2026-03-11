# Deployments [Prod]

## General
Deployment flow for the expected energy simulation.

## Deploy
### Local
- `mise run pveem:push-image`
- Reads the version from `pyproject.toml`.
- Reads the pinned `core==...` dependency from `pyproject.toml`.
- Pushes the Docker image to ECR with both `<version>` and `latest` tags.
- Publishes a single ARM64 image manifest that Lambda accepts.
- `mise run pveem:cdk-deploy`
- Defaults the CDK `imageTag` context to the same `pyproject.toml` version.
- `mise run pveem:deploy`
- Runs checks, pushes the image, then deploys CDK with
  `runtimeEnvironment=PROD`.
- If the current Lambda only has a `latest` tag, `pveem:deploy` performs the
  one-time semver tag migration automatically.

### Docker
- Image tags include both the `pyproject.toml` version and `latest`.
- Source `../_scripts/auth_aws_codeartifact.sh` before Docker builds.
- Production Docker installs the pinned `core` version from AWS CodeArtifact.
- ECR history lets you roll forward/backward by image tag.
- The push script disables `buildx` provenance and avoids `--push` so ECR does
  not receive a manifest/index variant that Lambda rejects.
- Test with `docker compose` locally before deployment.
- Docker is required because ZIP Lambda package size limits are too small.

### CDK
- Override the default image tag if needed:
  `mise run pveem:cdk-deploy -- -c imageTag=0.16.6`
- Override the Lambda runtime environment if needed:
  `mise run pveem:cdk-deploy -- -c runtimeEnvironment=PROD`

## Legacy SAM Cleanup
Use `pv-eem/_docs/readme/_README_DEPLOY.md` for the one-time checklist to
decommission `pv-expected-energy-lambda-stack` and `pv-simulation`.

## Useful Commands
- `uv export --frozen --no-dev`
- `docker compose up --build`
