# Mono
Mono-repo containing the api and web-ui, in the future we can add more services/libraries.


# Useful Commands

## Mise
- `brew install mise`:  Install the mise task runner
- `mise tasks`:  Discover mise tasks

## Core Dependency Management

The `core` package source is automatically switched based on your git branch:
- **dev**: Uses editable local install (`../core`) for active development
- **staging/main**: Uses AWS CodeArtifact for stable/release candidate versions

### Automatic Switching
The core dependency source is **automatically checked and updated** when you run:
- `mise run dev` - Starts development servers (checks on startup)
- `mise run switch-core` - Manually switch if needed

After switching branches, just run one of the above commands and the correct source will be configured automatically.

### Manual Check/Switch
```bash
# Check which source is currently configured
mise run check-core-source

# Manually switch based on current branch
mise run switch-core

# Apply changes (if source was switched)
uv sync
```

### How It Works
The `api/pyproject.toml` configuration is automatically updated based on your current git branch:
```toml
[tool.uv.sources]
core = { path = "../core", editable = true }  # Used on dev branch
core = { index = "proximal" }                  # Used on staging/main branches
```

### Optional: Git Hook Setup (Advanced)
For automatic switching on `git checkout`, team members can optionally run:
```bash
pre-commit install --hook-type post-checkout
```
This is **optional** since the dev task already handles it automatically.