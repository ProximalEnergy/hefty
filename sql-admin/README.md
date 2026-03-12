# Starlette Admin Application for Proximal Energy

A Starlette Admin application for FastAPI that provides a web-based admin
interface for managing the Proximal Energy core database.

## Features

- Web-based admin interface for core database tables
- Integration with existing core database and models
- Searchable and sortable columns
- Mirrors the old SQLAdmin page set, grouping, and CRUD permissions
- Supports targeting specific project schemas via `SQL_ADMIN_SCHEMA` or CLI argument

## Prerequisites

- The core PostgreSQL database must be running and accessible
- Environment variables must be configured (same as the main API)
- The `.env` file should contain the PostgreSQL DATABASE_URL

## Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Run the application:
   ```bash
   uv run python main.py
   ```

## Usage

Once running, navigate to `http://localhost:8001/admin` to access the admin
interface.

### Schema Selection

By default the app uses the `project_default` schema mapping. To target a
specific project schema, either set `SQL_ADMIN_SCHEMA=<schema_name>` in your
environment or pass the schema as the first CLI argument:

```bash
SQL_ADMIN_SCHEMA=project_name_short uv run python main.py
# or
uv run python main.py project_name_short
```

## Core Models Available

The application provides admin interfaces for:

### Admin Schema

- **Companies** - Company management
- **Users** - User management

### Operational Schema

- **Projects** - Project management
- **Project Types** - Project type definitions
- **Sensor Types** - Sensor type definitions
- **Device Models** - Device model catalog
- **KPI Types** - KPI type management
- **KPI Instances** - KPI instance management

### Project Schema

- **Devices** - Device management
- **Tags** - Tag management
- **Events** - Event management

> Note: Models with PostGIS/LTREE columns use explicit supported field lists so
> the old SQLAdmin pages still render in Starlette Admin.

## Port Configuration

The Starlette Admin application runs on port **8001** to avoid conflicts with
the main API (port 8000).

## Database Configuration

The application uses the same PostgreSQL database as your main API. Make sure
your `.env` file contains the correct `DATABASE_URL` pointing to your
PostgreSQL instance.
