# Mono
Mono-repo containing the api and web-ui, in the future we can add more services/libraries.


# Useful Commands

## Mise
- `brew install mise`:  Install the mise task runner
- `mise install`:  Install repo-managed tools, including Node.js and pnpm
- `mise tasks`:  Discover mise tasks
- `mise run dev`:  Run api and web-app servers together.
- `mise run check`:  Check all folders in mono-repo
- `mise run sync-deps`:  Sync all dependencies across mono
- `eval "$(mise activate zsh)"`:  Install in `.zshrc` for auto venv activation

### Mise Notes
- `Depends` will run all dependency tasks in parallel
- `Run` will run all tasks sequentially


# Onboarding
## Setup
- brew install mise
- mise install
- mise run onboarding

## PR's
- git switch -c Feature/pro-####-short-name (prefix branches with linear task id)