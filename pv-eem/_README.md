# --- Development --- [DEV]
Expected energy calculations for PV systems in Proximal

## Folder Structure General
- Folders with an _ are support folders.
- There are two **main** folders in this repository.
- There are three **minor** folders in this repository.
- There is a README.md in each of the main and minor folders.

## Main Folders
- **commissioning**:  Scripts meant to be run locally to commission projects so that they have the necessary information to be run in the simulation.
- **src**:  This folder contains the main simulation code.


## Minor Folders
- **_scripts**: Local scripts that are useful for developing this project, such as renaming step files.  This folder is like the miscellaneous drawer.
- **_tests**:  Local scripts that are useful for verifying the results of simulations.
- **_deploy**:  Documentation for deployments.  Also contains a _releases folder that is used to store release notes for each simulation version.


## Getting Started
- install uv for python package management:  `brew install uv`
  - uv is useful in this project because it allows you to differentiate between real dependencies and dependencies only needed for development.  By installing only real dependencies in the docker container, we can ensure faster cold starts.
  - `pyproject.toml` and `uv.lock` are the dependency source of truth.
  - local `uv sync` uses editable `core` from `../core`.
- install ruff for linting: `brew install ruff`
  - There are no strict linting rules for this project, but ruff still helps to keep the code relatively clean.
- Test locally by using `docker compose up`
  - source `../_scripts/auth_aws_codeartifact.sh` first
  - local docker container: `docker build -f Dockerfile -t pv-expected-energy .`
  - expose port 8080
  - mount aws volume


## Environment Variables
### Used in DEV and PROD environments
- ENVIRONMENT:  PROD | DEV
  - PROD:
    - will use SQL NOW() for instantaneous data
    - will export data to the Proximal database

  - DEV:
    - will use simulation_end - INTERVAL '24 hours' for instantaneous data
    - can be used to export data to parquet and plotly
    - can be used to export data to pickles for testing


### Used in local environment only
( The production environment uses an IAM role instead )
- DATABASE_URL: connection string for the target database
- AWS_ACCESS_KEY_ID: string
- AWS_SECRET_ACCESS_KEY: string
- AWS_S3_REGION: string
- AWS_S3_BUCKET_NAME: string


## CAVEATS
- Pandas will silently fail if you perform an operations that takes up too much memory.  This is unfortunate because you don't get an error message.


## Useful Commands:
  - `uv export --frozen --no-dev` shows the locked runtime dependency set.
  - `docker compose -f .docker-compose.yml up --build` will build the docker image and run it locally.
  - production Docker builds install the pinned `core==...` from
    `pyproject.toml` via AWS CodeArtifact.
  - `requirements.txt` and `requirements-dev.txt` are not used in this repo.


## Notes on Production Runs [Prod]
- 1 day of simulation at double_black_diamond (~592MW, ~3000 combiners)
  - Takes about 1 minute to run on cold start
  - Takes about 1 GB of memory
