# SQLAdmin Application for Proximal Energy

A SQLAdmin application for FastAPI that provides a web-based admin interface for managing the Proximal Energy core database.

## Features

- Web-based admin interface for core database tables
- Integration with existing core database and models
- Searchable and sortable columns
- Most tables are read-only for safety; KPI Instances support create and edit operations

## Prerequisites

- The core PostgreSQL database must be running and accessible
- Environment variables must be configured (same as the main API)
- The `.env` file should contain the PostgreSQL DATABASE_URL

## Quick Setup

Run the setup script to get started:

```bash
./setup.sh
```

This will:

- Install all dependencies including the core package
- Test the PostgreSQL database connection
- Verify the setup

## Manual Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Test PostgreSQL database connection:

   ```bash
   uv run python test_database_connection.py
   ```

3. Run the application:
   ```bash
   uv run python main.py
   ```

## Usage

Once running, navigate to `http://localhost:8001/admin` to access the admin interface.

## Core Models Available

The application provides admin interfaces for:

### Admin Schema (Read-Only)

- **Companies** - Company management
- **Users** - User management

### Operational Schema

- **Projects** - Project management (Read-Only)
- **Project Types** - Project type definitions (Read-Only)
- **Sensor Types** - Sensor type definitions (Read-Only)
- **KPI Instances** - KPI instance management (Create/Edit enabled)

### Project Schema (Read-Only)

- **Devices** - Device management
- **Tags** - Data tag management
- **Events** - Event management

## Port Configuration

The SQLAdmin application runs on port **8001** to avoid conflicts with the main API (port 8000).

## Database Configuration

The application uses the same PostgreSQL database as your main API. Make sure your `.env` file contains the correct `DATABASE_URL` pointing to your PostgreSQL instance.
