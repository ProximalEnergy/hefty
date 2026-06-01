# Onboarding

## Commands
- `mise onboarding`
- `mise check`

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
