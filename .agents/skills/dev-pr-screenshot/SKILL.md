---
name: dev-pr-screenshot
description: >-
  Automate local pull request preparation against the dev branch,
  including branch diff labeling (api/core/web-app/etc.), PR title and
  body generation with required sections, and web-app screenshot
  capture for Testing evidence. Use when finishing feature work and
  creating a PR that needs consistent metadata and visual validation.
---

# Dev PR Screenshot

## Overview

Use this skill to standardize PRs against `dev` in a mono-repo. It detects which
areas changed, builds a bracketed PR prefix (for example `[api, web-app]`),
creates the required PR body sections, and captures web-app screenshots for the
`# Testing` section.

## Workflow

1. Run `.agents/skills/dev-pr-screenshot/scripts/prepare_pr.sh` to detect
   changed repo areas versus `dev`, commit local changes, push the branch, and
   open the PR.
2. Review the generated title prefix and body template output.
3. If web-app changed, run the app and capture relevant screenshots.
4. Upload screenshots and insert markdown image links in `# Testing`.
5. Re-run the script after adding screenshot/video files if you want them
   included in the PR body.
6. As the final step, summarize recent git logs into:
   Features, Refactors, and Bugfixes.

## Commands

### Run full PR flow

```bash
./.agents/skills/dev-pr-screenshot/scripts/prepare_pr.sh
```

The script prints:

- A detected title prefix like `[api, core]`
- A generated PR body based on `pull_request_template.md`
- It then commits, pushes, and creates the PR using that generated body

### 2) Optional: Capture screenshots for web-app changes

Only do this when `web-app` is part of the prefix.

- Start app locally (example): `cd web-app && npm run dev -- --host 0.0.0.0`
- Use Playwright (or Codex browser tool) to capture relevant pages.
- Save images in a predictable folder such as `artifacts/pr-screenshots/`.

### 3) Populate `# Testing`

In the PR body, include:

- Commands run (lint/test/build)
- Screenshot links:

```markdown
![dashboard page](artifacts/pr-screenshots/dashboard.png)
![settings page](artifacts/pr-screenshots/settings.png)
```

If running in a sandboxed environment:
- Run the command with escalated permissions for `.git` writes.
- Ensure network-enabled escalation is available for `gh pr create`.

### 4) Final summary from git logs

After the PR body/screenshots are prepared, summarize git history in three
sections using:

```bash
./.agents/skills/dev-history-summary/scripts/summarize_dev_history.sh --days 14
```

Then produce markdown with:
- `## Features`
- `## Refactors`
- `## Bugfixes`

## Notes

- Keep `# Reasoning for Changes` present but empty unless explicitly requested.
- Keep the prefix list to changed areas only.
- If no mapped area is detected, use `[misc]`.
