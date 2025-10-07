# Post-Migration Checklist

This checklist should be completed after the Poe to Mise migration to ensure everything is working correctly.

## Immediate Actions Required

### 1. Update Lock Files
The `uv.lock` files still contain references to `poethepoet` and need to be regenerated:

```bash
# In api directory
cd api
uv lock

# In core directory
cd ../core
uv lock
```

**Why**: The lock files track all dependencies, and we've removed `poethepoet` from `pyproject.toml`.

### 2. Install Mise (Each Developer)
Every developer needs to install mise on their local machine:

```bash
# Option 1: Direct install
curl https://mise.run | sh

# Option 2: Homebrew (macOS)
brew install mise

# Add to shell configuration
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc    # for zsh
echo 'eval "$(mise activate bash)"' >> ~/.bashrc  # for bash

# Restart shell or source the config
source ~/.zshrc  # or ~/.bashrc
```

**Verify installation**:
```bash
mise --version
```

### 3. Verify Task Availability
Test that mise can find and list tasks:

```bash
# From api directory
cd api
mise tasks

# From core directory
cd ../core
mise tasks
```

**Expected output**: Should list all available tasks defined in `.mise.toml`

### 4. Test Core Tasks
Verify that the most commonly used tasks work:

```bash
cd api
mise run check          # Should run all quality checks
mise run types          # Should run type checking
mise run core_auto      # Should detect branch and install core

cd ../core
mise run check          # Should run all quality checks
mise run types          # Should run type checking
```

## Team Communication

### 5. Notify Team Members
Share the following with the team:

- [ ] Migration has been completed
- [ ] Link to [MIGRATION_POE_TO_MISE.md](./MIGRATION_POE_TO_MISE.md)
- [ ] Link to [MISE_QUICK_REFERENCE.md](./MISE_QUICK_REFERENCE.md)
- [ ] Installation instructions for mise
- [ ] Timeline for when everyone should complete migration

### 6. Update Team Documentation
If you maintain additional documentation (Confluence, Notion, etc.), update:

- [ ] Development setup guides
- [ ] Onboarding documentation
- [ ] CI/CD runbooks (if applicable)
- [ ] Troubleshooting guides

## Optional Improvements

### 7. Add Mise to CI/CD (If Needed)
If your CI/CD pipelines were using poe commands, update them:

```yaml
# Example: GitHub Actions
- name: Install mise
  run: curl https://mise.run | sh

- name: Run checks
  run: mise run check
```

**Note**: Based on grep results, no GitHub workflows were using poe directly, so this may not be needed.

### 8. Clean Up Old Aliases
If team members had shell aliases for poe commands:

```bash
# Remove from ~/.zshrc or ~/.bashrc
alias check="poe check"        # Remove these
alias types="poe types"        # Remove these

# Optional: Add new mise aliases
alias check="mise run check"
alias types="mise run types"
```

### 9. Pre-commit Hooks (Optional)
Consider adding mise tasks to pre-commit hooks:

```yaml
# .pre-commit-config.yaml (if it exists)
- repo: local
  hooks:
    - id: mise-check
      name: Run mise check
      entry: mise run check
      language: system
      pass_filenames: false
```

## Verification Tests

### 10. Run Full Test Suite
Ensure nothing broke during migration:

```bash
# API tests
cd api
mise run pytest
mise run hurl

# Core tests
cd ../core
mise run pytest
```

### 11. Test Core Installation Workflow
Verify the core version management still works:

```bash
cd api

# Test each core installation method
mise run core_auto      # Should auto-detect branch
mise run core_beta      # Should install beta version
mise run core_rc        # Should install RC version
mise run core_stable    # Should install stable version
```

### 12. Test Release Workflow (Core)
In a test branch, verify the release process:

```bash
cd core
git checkout -b test-release-workflow

# Test bump
mise run bump patch
# Verify version was bumped in pyproject.toml

# Don't actually release, just verify the command works
git checkout main
git branch -D test-release-workflow
```

### 13. Test Database Migration (Core)
Verify the db task works (don't actually create a migration):

```bash
cd core

# Test the command syntax (Ctrl+C before it completes)
mise run db "Test migration message"
# Verify it starts alembic correctly, then cancel
```

## Documentation Review

### 14. Review All Documentation Updates
Verify these files were updated correctly:

- [ ] `AGENTS.md` - References to mise instead of poe
- [ ] `README.md` - New mise section added
- [ ] `api/README.md` - All poe commands replaced with mise
- [ ] `core/README.md` - All poe commands replaced with mise
- [ ] `_scripts/verify_versioning_setup.sh` - Checks for mise instead of poe
- [ ] `core/_alembic_migrations/_README_ALEMBIC.md` - References mise
- [ ] `core/pull_request_template.md` - References mise

### 15. Verify New Documentation
Ensure these new files are complete and accurate:

- [ ] `MIGRATION_POE_TO_MISE.md` - Comprehensive migration guide
- [ ] `MISE_QUICK_REFERENCE.md` - Quick reference card
- [ ] `CHANGES_SUMMARY.md` - Complete list of changes
- [ ] `POST_MIGRATION_CHECKLIST.md` - This file

## Cleanup

### 16. Remove Old Poe References
Search for any remaining poe references you might have missed:

```bash
# Search for any remaining poe references
grep -r "poe " --include="*.md" --include="*.sh" --include="*.py" . | grep -v "MIGRATION\|CHANGES_SUMMARY\|POST_MIGRATION\|MISE_QUICK_REFERENCE"

# Should return no results (except in migration docs)
```

### 17. Update Dependencies
After lock files are updated, sync dependencies:

```bash
cd api
uv sync

cd ../core
uv sync
```

## Rollback Plan (If Needed)

If critical issues are discovered:

### 18. Emergency Rollback Steps

```bash
# Revert the pyproject.toml files
git checkout HEAD~1 -- api/pyproject.toml core/pyproject.toml

# Remove mise config files
rm api/.mise.toml core/.mise.toml

# Restore lock files
git checkout HEAD~1 -- api/uv.lock core/uv.lock

# Reinstall dependencies
cd api && uv sync
cd ../core && uv sync

# Revert documentation
git checkout HEAD~1 -- AGENTS.md README.md api/README.md core/README.md

# Notify team to use poe commands again
```

## Success Criteria

The migration is considered successful when:

- [ ] All developers have mise installed
- [ ] Lock files are updated and don't contain poethepoet
- [ ] All tasks run successfully with `mise run <task>`
- [ ] No team member is blocked by the migration
- [ ] All documentation is updated and accurate
- [ ] CI/CD pipelines work (if applicable)
- [ ] No bugs introduced by the migration

## Timeline Recommendations

| Task | When | Who |
|------|------|-----|
| Update lock files | Immediately | Migration lead |
| Install mise locally | Within 1 day | All developers |
| Verify tasks work | Within 1 day | All developers |
| Update team docs | Within 2 days | Tech lead |
| Full team adoption | Within 1 week | All team members |

## Support

If you encounter issues:

1. Check [MIGRATION_POE_TO_MISE.md](./MIGRATION_POE_TO_MISE.md) troubleshooting section
2. Check [MISE_QUICK_REFERENCE.md](./MISE_QUICK_REFERENCE.md) for command syntax
3. Review mise documentation: https://mise.jdx.dev/
4. Ask in team chat
5. Create an issue in the repository

## Notes

- The migration is designed to be non-breaking
- All functionality remains the same, only the tool changed
- Mise is backwards compatible with most poe features
- Performance should be noticeably faster with mise

## Completion

Once all items are checked off:

- [ ] Mark this migration as complete in project tracking
- [ ] Archive this checklist (or keep for reference)
- [ ] Consider deleting old migration docs after 30 days (optional)
- [ ] Celebrate! 🎉

---

**Migration Date**: January 2025  
**Last Updated**: January 2025