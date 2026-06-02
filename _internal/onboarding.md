# Onboarding
## General
Welcome to Proximal's main mono repo.  In this repo we hold a set of services that are all supported by the main `core` library.  Each service is represented by a single folder in the mono repo and each servie is deployed separately from every other service.

## Important Commands
- `mise onboarding`
- `mise check`

## Important Tools
- `mise`:  task runner, tool environment manager
- `uv`:  python package managment

## Architecture
- The 3 Main Folders
  - `core`: library with shared functions
  - `api`:  api
  - `web-app`:  front end
- Everything Else
  - various other services and micro services that support our three main services

## Important Classes
- `DbQuery`:  
  - Any CRUD operation that hits our database should use this.
  - Reduces errors for database ops like using sync or not separating query definition from execution
- `DataTimeseries`:
  - Any READ operation that hits our timeseries database should use this.
  - Reduces errors for timeseries database gets

## Process
- Create a branch off of `dev`
- Do your work, commit frequently
- Use `mise check` periodically to run fast check suite
- When complete:
  - Run `mise check`, make sure everything passes
  - Run start `codex` run `/review` against `dev`
  - Create pull request from `your branch` onto `dev`
  - Pull requests should be as small as possible, ideally less than 500 lines of code.

## Agents
- use `plan` and `execute` skills to give agents context about our codbase
