---
name: solving-linear-issues
description: >-
  Use when asked to solve Linear issue, such as "linear PRO-660",
---

# Solving Linear Issues

## Useful Skills
- plan
- execute

## Workflow

1. Review Linear issue through Linear MCP by searching for 
   issue `identifier` exactly, for example `PRO-660`.
2. In mono repo, switch to `dev` and run `mise run sync` to synchronize
   `dev` with `origin`.
3. Create a new branch:
   - Use `bugfix/pro-xxx-some-descriptive-name` for a bugfix issue.
   - Use `feature/pro-xxx-some-descriptive-name` for a new feature or update
     to an existing feature.
   - Keep `pro-xxx` lowercase and make the descriptive suffix short.
4. Make the code changes needed to solve the Linear issue. Keep edits scoped
   to the issue and protect unrelated user changes in the working tree.
5. Run `mise run check`.
   - If it fails, fix the issue and repeat `mise run check`.
   - Do not ignore knip, mypy, ruff, TypeScript, lint, or test failures.
6. Draft the pull request in markdown using `pull_request_template.md` from
   the repo root.
   - Do not submit or create the PR until the user approves.
   - Keep the PR description focused on the core issue and changes.
   - Include the verification performed.

## PR Title

- Prefix the title with the main folders modified, such as `[core]`,
  `[web-app]`, `[api]`, or `[core, web-app]`.
- Use `Feature:` for new functionality or updates to existing features.
- Use `Bugfix:` for bug fixes.
- Preserve the Linear identifier in uppercase.
- Use pull_request_template.md

## If Anything Is Unclear

Ask before proceeding if:

- The Linear issue cannot be found.
- The issue type is ambiguous between bugfix and feature.
- There are unrelated local changes that block switching branches.
- The requested fix conflicts with existing product behavior or architecture.
