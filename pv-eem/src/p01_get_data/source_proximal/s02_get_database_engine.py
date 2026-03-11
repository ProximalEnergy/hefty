import sqlalchemy
from sqlalchemy.pool import NullPool


def get_db_engine(*, database_url: str):
    """Run get_db_engine."""
    engine = sqlalchemy.create_engine(
        database_url,
        connect_args={
            "application_name": "PV_EEM",
            "options": "-c application_name=PV_EEM",
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        },
        poolclass=NullPool,
    )

    return engine
