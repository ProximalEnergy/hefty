# Deployments [Prod]

## General
Deployment flow for the expected energy simulation.

## [PROD]
### GitHub Actions
- Workflow: `.github/workflows/deploy.yml`
- Trigger: version tags (`v*`) pushed to a commit.
- Validate: tag version must match `pyproject.toml`.
- Build: Docker image is pushed to ECR with release and `latest` tags.
- Deploy: CDK in `events/` deploys Lambda `pv-eem` and EventBridge rules.

### Docker
- Image tags include both release tag and `latest`.
- ECR history lets you roll forward/backward by image tag.
- Test with `docker compose` locally before production deploys.
- Docker is required because ZIP Lambda package size limits are too small.

## [Stage]
### CDK
- `mise run pveem:cdk-deploy`
- Optional image tag:
  `mise run pveem:cdk-deploy -- -c imageTag=v0-16-6`

## Legacy SAM Cleanup
Use `pv-eem/_docs/readme/_README_DEPLOY.md` for the one-time checklist to
decommission `pv-expected-energy-lambda-stack` and `pv-simulation`.

## Useful Commands
- `uv export --frozen --no-emit-workspace --no-dev --no-editable \
  -o requirements.txt --no-hashes`
- `docker compose up --build`
