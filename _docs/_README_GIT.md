# Git Workflow

## Feature branches
- `git rebase dev`
- Standard commits into feature branch
- Open PR when done

## Downstream Deployments
- Squash merge feature branch into dev
- Standard merge dev branch into staging
- Standard merge staging branch into main

## Upstream Fixes
- Rebase staging onto main
- Rebase dev onto staging

### Diverged Git History
- New branch off of dev
- git merge --squash -X ours feature_branch_name


## (Optional)
### Pre-Commit Hooks
Useful files:
 - Config:  `.pre-commit-config.yaml`
Useful commands:
 - `pre-commit install`
