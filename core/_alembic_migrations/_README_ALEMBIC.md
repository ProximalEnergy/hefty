# Database Migrations

## TLDR
- Database migrations are managed by `alembic`
- alembic itself is controlled by `alembic.ini`

## Alembic Database Migrations

Alembic is used to manage database migrations. Alembic directly compares the SQLAlchemy models defined in `core/src/core/models.py` with the current state of the database to detect any changes. Below are a few common commands used to run migrations.

- `alembic revision --autogenerate -m "<message>"` - Create a new migration file that will be saved to `_alembic_migrations/versions`. This command will not make any changes to the database.
- `alembic upgrade head` - Run the latest migration script. This WILL make changes to the database. **IMPORTANT** - Only the database admin should push changes to the production database.
- `alembic downgrade -1` - Downgrade to the previous version. This WILL make changes to the database.

Check `.mise.toml` for some helpful `mise` commands (e.g., `mise run db "message"`).

You can verify a migration was successful by inspecting the database. The Alembic version is also stored in the `public.alembic_version` table. This version should match the `revision` variable generated in the latest migration. More information can be found in the Alembic [documentation](https://alembic.sqlalchemy.org/en/latest/).

### Migration Scripts

Alembic migration scripts will be automatically generated using the template at `alembic_migrations/script.py.mako`. By default, a custom decorator is imported from `alembic_migrations/tenant.py` that allows for running a single migration for all project schemas. When running these migrations, any reference to the `"project_default"` schema in the bodies of the `upgrade` and `downgrade` functions needs to be replaced with the `schema` argument. When running migrations for non-project schemas, the decorator, import, and `schema` argument should be removed. If necessary, migrations can be split into multiple iterations.
