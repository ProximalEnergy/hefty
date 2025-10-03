# Core Library Bundling Migration Guide

## Summary

The API deployment to Elastic Beanstalk has been migrated from using AWS CodeArtifact to **bundling the `core` library directly** into the deployment package.

## What Changed

### Before (CodeArtifact Approach)
```
┌─────────────┐
│   GitHub    │
│   Actions   │
└─────┬───────┘
      │
      ├─ Authenticate with AWS CodeArtifact
      ├─ Download core package (0.2.43b4)
      ├─ Install dependencies
      └─ Deploy to Elastic Beanstalk
```

### After (Bundled Approach)
```
┌─────────────┐
│   GitHub    │
│   Actions   │
└─────┬───────┘
      │
      ├─ Copy core/src/core/* → api/core/
      ├─ Generate requirements.txt (without core)
      ├─ Zip everything together
      └─ Deploy to Elastic Beanstalk
```

## Benefits

✅ **No AWS CodeArtifact authentication needed** during API deployment
✅ **Faster deployments** - no external package registry lookups
✅ **Always synchronized** - core version matches the API code
✅ **Simpler infrastructure** - one less service to manage
✅ **Better for monorepo** - leverages the fact that both are in the same repository

## What Still Uses CodeArtifact

The `core` library **continues to be published** to AWS CodeArtifact for:
- Other microservices that depend on core
- External systems that need to consume core
- Backward compatibility with existing services

**The change only affects the API deployment to Elastic Beanstalk.**

## Files Changed

### New Files
- `mono/api/.ebignore` - Defines files to exclude from EB deployment
- `mono/api/DEPLOYMENT.md` - Comprehensive deployment documentation
- `mono/api/_scripts/test_deployment_package.sh` - Local testing script
- `mono/CORE_BUNDLING_MIGRATION.md` - This file

### Modified Files
- `mono/.github/workflows/api-deploy.yml` - Updated deployment workflow
  - Removed CodeArtifact authentication step
  - Removed `CORE_VERSION_TYPE` environment variable
  - Added core library copying step
  - Updated requirements.txt generation to exclude core
- `mono/api/.ebextensions/01_fastapi.config` - Added verification command
- `mono/api/README.md` - Updated with deployment information
- `mono/api/pyproject.toml` - Added `test_deploy` poe task


## Deployment Workflow Changes

### Old Workflow Steps
1. Checkout code
2. Install uv
3. **Configure AWS credentials** ← REMOVED
4. **Authenticate with CodeArtifact** ← REMOVED
5. **Update core dependency from CodeArtifact** ← REMOVED
6. Generate requirements.txt (with core==0.2.43b4)
7. Package deployment
8. Deploy to Elastic Beanstalk

### New Workflow Steps
1. Checkout code
2. Install uv
3. **Copy core library source to api/core/** ← NEW
4. Generate requirements.txt (without core) ← MODIFIED
5. Package deployment (with bundled core)
6. Deploy to Elastic Beanstalk

## Local Development - No Changes

**Local development is unchanged!** You still use workspace dependencies:

```bash
# Install dependencies (
