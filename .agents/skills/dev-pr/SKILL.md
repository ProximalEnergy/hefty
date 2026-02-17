---
name: dev-pr
description: >-
  Automate local pull request preparation against the dev branch,
  including branch diff labeling (api/core/web-app/etc.), PR title and
  body generation with required sections. Use when finishing feature
  work and creating a PR that needs consistent metadata.
---

# Dev PR Screenshot

## Overview

Use this skill to standardize PRs against `dev` in a mono-repo. It detects which
areas changed, builds a bracketed PR prefix (for example `[api, web-app]`),
and creates the required PR body sections.

## Workflow

1. Run `.agents/skills/dev-pr/scripts/prepare_pr.sh` to detect
   changed repo areas versus `dev`, commit local changes, push the branch, and
   open the PR.
2. Review the generated title prefix and body template output.

## Commands

### Run full PR flow

```bash
./.agents/skills/dev-pr/scripts/prepare_pr.sh
```

The script prints:

- A detected title prefix like `[api, core]`
- A generated PR body based on `pull_request_template.md`
- It then commits, pushes, and creates the PR using that generated body

### 2) Populate `# Testing`

In the PR body, include:

- Commands run (lint/test/build)

If running in a sandboxed environment:
- Run the command with escalated permissions for `.git` writes.
- Ensure network-enabled escalation is available for `gh pr create`.

## Notes

- Keep `# Reasoning for Changes` present but empty unless explicitly requested.
- Keep the prefix list to changed areas only.
- If no mapped area is detected, use `[misc]`.
