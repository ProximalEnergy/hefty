# Mono
Mono-repo containing the api and web-ui, in the future we can add more services/libraries.

Main

# Useful Commands

## Git
`git subtree add --prefix=FOLDER REPO_URL BRANCH --squash`: Add a new repository
`git subtree pull --prefix=FOLDER REPO_URL BRANCH --squash`: Update repository
`source _scripts/subtree.sh`:  Update all repositories

## Docker
- `docker compose watch`:  Run api and web-app with hot reload
- `docker compose up`:  Run api and web-app without hot reload
- `docker compose down`: Take both services down
