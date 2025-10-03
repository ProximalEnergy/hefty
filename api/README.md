# Proximal API

## Deployment

The API is deployed to AWS Elastic Beanstalk with the `core` library **bundled directly** into the deployment package. This means:

- ✅ No AWS CodeArtifact authentication needed during deployment
- ✅ Faster deployments (no external package lookups)
- ✅ Core library version is always synchronized with API code
- ✅ Simpler infrastructure

### How Core is Deployed

When deploying to Elastic Beanstalk:
1. The CI/CD pipeline copies `core/src/core/*` → `api/core/`
2. The core library is bundled directly into the deployment package
3. Requirements.txt is generated **without** the core dependency
4. Everything is zipped and deployed together

**For other services**: The `core` library continues to be published to AWS CodeArtifact for services outside this API.

📖 For complete deployment documentation, see [DEPLOYMENT.md](./DEPLOYMENT.md)

### Test Deployment Package Locally

```bash
# Test that the deployment package structure is correct
poe test_deploy
```

## Local Development with Core

For **local development**, the `core` library is used as a workspace dependency (not bundled):

### Quick Start: Install Core for Your Branch

```bash
# Auto-detect your current branch and install the appropriate core version
poe core_auto
```

### Manual Core Version Selection

```bash
# Install latest beta version (for dev branch)
poe core_beta

# Install latest RC version (for staging branch)
poe core_rc

# Install latest stable version (for main/production branch)
poe core_stable

# Install editable local core (for active core development)
poe e_core  # requires CORE_PATH in .env
```

### Core Package Versioning

The `core` package is published in different versions based on the environment:

- **Beta** (`0.2.43b1`) - Latest development version from `dev` branch
- **Release Candidate** (`0.2.43rc1`) - Pre-release version from `staging` branch  
- **Stable** (`0.2.43`) - Production version from `main` branch

**Note**: These versioning commands are for local development and other services that consume core from CodeArtifact. The API deployment to Elastic Beanstalk uses the bundled approach described above.

📖 For complete versioning documentation, see [VERSIONING.md](../VERSIONING.md)

## Local Development

- To start the API locally, run `fastapi dev` or `uv run uvicorn app.main:app --reload` from the root of the project directory.

### Environments

- Environments are managed by `uv` which creates a `requirements.txt`
- Some useful `uv` commands:
  - `uv venv ...`: Create a virtual environment
  - `uv sync`: Update dependencies to be consistent with `pyproject.toml` file
  - `uv pip ...`: Uv is backwards compatible with pip
  - `uv run ...`: Preface for running any python command
  - `uv add ...`: Add a requirement to pyproject.toml and uv.lock
  - `uv remove ...`: Remove a requirement from pyproject.toml and uv.lock
  - `uv export > requirements.txt`: Create full requirements.txt
    - `--no-hashes`: No hashes
    - `--no-dev `: Don't include development dependencies
    - `--frozen`: Pin dependencies to a specifric version
  - `poe freeze` or `uv export --frozen --no-emit-workspace --no-dev --no-editable -o requirements.txt --no-hashes`: For AWS environments
  - `poe types` or `uv run mypy --config-file pyproject.toml -p app`: Locally run type-checks (not included in pre-commit hook)

Make sure to install PostgreSQL before running `uv sync` the first time.

```
>>> brew install postgresql
```

### Environment Variables

When running locally the following environment variables are required

- `ENVIRONMENT`: Distinguishes between `"development"` and `"production"`
- `EXCEL_PATH`: Set to user's Downloads folder. Used to retrieve data during manual inserts.
- `DATABASE_URL`: Standard database URL used to create the SQLAlchemy engine
- `CONNECTION_STRING`: Similar to the DATABASE_URL, but using the `"host=<...> port=<...>"` format. Used for all of the data insert scripts (does not use the connection pooler).
- `URL_JWKS(\_DEVELOPMENT)`: Used for Clerk authentication
- `CLERK_SECRET_KEY(\_DEVELOPMENT)`: Used for Clerk authentication
- `WEATHER_API_KEY`: Used to retrieve OpenWeather data
- `OPENAI_API_KEY`: Used to interact with OpenAI
- S3 Variables
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_S3_REGION`
  - `AWS_S3_BUCKET_NAME`
- `COMMISSIONING_KEY_JSON`: Used for google sheets

You can pull the environment variables from AWS Secrets with

```
>>> poe get_env
```

which creates a `.env.from_secrets` file whose contents can be copied into your actual `.env` file. This command requires AWS authentication which can be setup with

```
>>> aws configure
```

Staging and production environment variables are hosted on Elastic Beanstalk.

### Debugging

To run the application in debug mode, set up a debug configuration file that looks similar to the following.

```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--reload"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

## Folder Structure

The api repository is a monolith which includes both the API transport layer of the application and the business/domain logic in the same repository.

At the top level:

- `app`: The main monolith
- `_alembic_migrations`: Scripts for database migrations
- `_data_insert`: Scripts for inserting data into database
- `_variable`: Scripts for doing something

- `app`: The main monolith
- `_alembic_migrations`: Scripts for database migrations
- `data_insert`: Scripts for inserting data into database
- `_variable`: Scripts for doing something

## SQLAlchemy Models

### Best Practices

- Table names should be plural and lower_case_snake_case (i.e. "solar_projects").
- Model class names should be singular PascalCase (i.e. "SolarProject").
- Column names should be lower_case_snake_case (i.e. "dc_capacity").
- If a model has a singular primary key ID column, it should be named as the singular version of the table name (i.e. "solar_project_id").

### Default Schema

Throughout the application, the default schema is the `project_default` schema. This schema is used in place of each project specific schema, and the translation between the two is handled in Alembic migrations and FastAPI database connections.

When creating a new model that will live outside of a project schema, make sure to indicate as such in the `__table_args__` attribute like `__table_args__ = {"schema": "<schema_name>"}`.

### Default `autoincrement` behavior

By default, a model defined to have an INTEGER primary key with no other defaults will be assigned auto increment semantics automatically. See more in the SQLAlchemy docs [here](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Column.params.autoincrement). Pass `autoincrement=False` to the `mapped_column` constructor to avoid this behavior.

### Timescale Integration

Neither Alembic nor SQLAlchemy have direct support for Timescale. Because of this, it is necessary to add a custom statement in the Alembic migration script. Simply add a line similar to the following code block.

```
op.execute(
    """
    SELECT create_hypertable('<table_name>', by_range('time'));
    """
)
```

Note, `<table_name>` should include the schema if necessary. For more information see the Timescale `create_hypertable` [documentation](https://docs.timescale.com/api/latest/hypertable/create_hypertable/).

## Manual Data Inserts

### Downloading data from Drive

Metadata tables are stored in Google Drive [here]("https://drive.google.com/drive/folders/17jehLoDv7oospRQfV5D3Jv3r9G0jTq-g?usp=drive_link"). Data (whether it be `_operational.xlsx` or a project workbook) needs to be downloaded your local machine before running the insert scripts. The value of `EXCEL_PATH` in the `.env` file should be set to the path of the folder containing the downloaded data.

### Inserting data into the database

Scripts in the `data_insert` folder are used to manually insert data into the database. In order to run these scripts, `CONNECTION_STRING` and `EXCEL_PATH` need to be defined in a `.env` file. To run the insert scripts, use the `python -m` module syntax. For example, run `python -m _data_insert.operational.1_data_types`.
There are `poe` convenience functions for some of the insert scripts. Currently supported are:
  - project.tags
    - `poe insert_tags {project_name_short}`
  - operational.kpi_types
    - `poe insert_kpi_types`
  - operational.kpi_instances
    - `poe insert_kpi_instances`
