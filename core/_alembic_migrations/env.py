import sys
from logging.config import fileConfig

from alembic import context

# Import settings to ensure environment variables are loaded
from core.settings import DATABASE_URL
from sqlalchemy import MetaData, engine_from_config, pool, text

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config


def escape_config_parser_interpolation(*, value: str) -> str:
    return value.replace("%", "%%")


# Set the SQLALchemy database URL
config.set_main_option(
    "sqlalchemy.url",
    escape_config_parser_interpolation(value=DATABASE_URL),
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# target_metadata = None

# Import all models so they are registered with Base.metadata
import core.models  # noqa: F401, E402
from core.database import Base  # noqa: E402

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    translated = MetaData()

    for table in target_metadata.tables.values():
        table.to_metadata(
            translated,
            schema="project_default" if table.schema == "project" else table.schema,
        )

    def include_name(
        name, type_, parent_names
    ):  # nosemgrep: python-enforce-keyword-only-args
        if type_ == "schema":
            return name in (
                "public",
                "admin",
                "operational",
                "project_default",
                "ercot",
            )
        else:
            return True

    def include_object(
        object, name, type_, reflected, compare_to
    ):  # nosemgrep: python-enforce-keyword-only-args
        if type_ == "table":
            return object.schema in ("admin", "operational", "project_default", "ercot")
        else:
            return True

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=translated,
            include_name=include_name,
            include_object=include_object,
            # Scan across all schemas
            include_schemas=True,
            # Nest each migration script in a transaction
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            # Add a lock timeout
            # See more at https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-LOCK-TIMEOUT
            context.execute(sql=text("SET lock_timeout = '5s'"))

            # Add a statement timeout
            # See more at https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-STATEMENT-TIMEOUT
            context.execute(sql=text("SET statement_timeout = '30s'"))

            context.run_migrations()


# Check if this is an upgrade command by looking at sys.argv
if len(sys.argv) > 1 and sys.argv[1] == "upgrade":
    confirmation = input(
        "🚦 Are you sure there are no public demos in progress or upcoming? "
        "(Type 'y' to confirm): "
    )

    # Check if the user's input is 'k', ignoring case and whitespace
    if confirmation.strip().lower() != "y":
        # Exit the script cleanly without running the migration
        sys.exit(0)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
