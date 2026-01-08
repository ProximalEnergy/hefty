import uuid
from datetime import timedelta

import httpx
import sqlalchemy as sa
from core.database import Base
from core.enumerations import ProjectDataInterval, ProjectStatusType
from core.models import Project as DBProject
from fastapi import HTTPException
from shapely.geometry import Point
from sqlalchemy import Interval
from sqlalchemy.ext.asyncio import AsyncSession
from timezonefinder import TimezoneFinder

from app._crud.admin.companies import get_companies
from app._crud.admin.user_projects import (
    assign_project_to_relevant_users,
)
from app._crud.admin.users import get_user
from app.domain.internal_comms.comms import (
    CommunicationChannel,
    send_project_creation_notification,
)
from app.interfaces import Project, ProjectCreate
from app.logger import logger


def _get_operational_and_project_metadata():
    """Get metadata for operational, project, and admin schema tables.

    Admin schema is included because project tables may have foreign keys
    to admin tables (e.g., event_messages.user_id -> admin.users.user_id).
    """
    meta = sa.MetaData()
    for table in Base.metadata.tables.values():
        if table.schema in ["operational", "project", "admin"]:
            _ = table.to_metadata(meta)
    return meta


async def _create_schema_and_tables(
    *,
    db: AsyncSession,
    name_short: str,
    do_commit: bool = True,
) -> None:
    """
    Create project schema and tables for a new project.

    Args:
        db: The SQLAlchemy database session.
        name_short: The short name of the project (used as schema name).
        data_timeseries_chunk_interval: The chunk interval for data_timeseries
        hypertable.
        do_commit: Whether to commit the transaction. Defaults to True.
                  Set to False for atomic operations where commit is handled externally.
    """
    schema = name_short

    try:
        # Create new project tables
        # NOTE: We need to retrieve the operational tables as well so that the
        # ForeignKey constraints in the project tables will work. The db engine
        # needs to "know" about tables that are referenced in ForeignKey
        # constraints.
        metadata = _get_operational_and_project_metadata()

        # Filter for tables in the 'project' schema and set their schema to the new
        # project's short name
        project_tables = []

        # First pass: collect all tables that need schema updates
        tables_to_copy = []
        for table in list(metadata.tables.values()):
            # if table.key in ["project.data", "project.data_raw"]:
            #     continue
            if table.schema == "project":
                tables_to_copy.append(table)

        # Second pass: create new tables with updated schema
        # Create a separate metadata object to avoid modifying existing metadata
        new_metadata = sa.MetaData()

        # Copy operational and admin tables to new metadata (needed for foreign
        # key constraints)
        # Admin tables are not created in project schema, but metadata needs to
        # know about them
        # for foreign key resolution
        for table in metadata.tables.values():
            if table.schema in ["operational", "admin"]:
                table.to_metadata(new_metadata)

        # Create project tables with new schema
        for table in tables_to_copy:
            new_table = table.to_metadata(new_metadata, schema=schema)
            project_tables.append(new_table)

        # Third pass: update foreign key references to use the correct schema
        for new_table in project_tables:
            # Collect foreign keys that need updating
            fks_to_update = []
            for fk in new_table.foreign_keys:
                if fk.column.table.schema == "project":
                    fks_to_update.append((fk, fk.column.table))

            # Apply the schema updates
            for fk, referenced_table in fks_to_update:
                referenced_table.schema = schema

        def ddl(sync_session):  # nosemgrep: python-enforce-keyword-only-args
            """todo

            Args:
                sync_session: TODO: describe.
            """
            conn = sync_session.connection()  # sync Connection bound to the same txn
            conn.execute(sa.schema.CreateSchema(schema, if_not_exists=True))
            new_metadata.create_all(bind=conn, tables=project_tables, checkfirst=True)

        await db.run_sync(ddl)

        # For more information, view the TigerData documentation using the links below
        # https://docs.tigerdata.com/api/latest/hypertable/create_hypertable/
        # https://docs.tigerdata.com/api/latest/hypercore/alter_table/

        # If data_timeseries is in new_metadata, add hypertable
        if f"{schema}.data_timeseries" in new_metadata.tables.keys():
            await db.execute(
                sa.text(
                    f"""
                    SELECT create_hypertable(
                        '{schema}.data_timeseries',
                        by_range('time', :chunk_interval)
                    );
                    """
                )
                .bindparams(sa.bindparam("chunk_interval", type_=Interval()))
                .params(chunk_interval=timedelta(days=1))
            )
            await db.execute(
                sa.text(
                    f"""
                    ALTER TABLE {schema}.data_timeseries SET (
                        timescaledb.enable_columnstore = true,
                        timescaledb.orderby = 'time DESC',
                        timescaledb.segmentby = 'tag_id'
                    );
                    """
                ),
            )

        # If data_expected is in new_metadata, add hypertable
        if f"{schema}.data_expected" in new_metadata.tables.keys():
            await db.execute(
                sa.text(
                    f"""
                    SELECT create_hypertable(
                        '{schema}.data_expected',
                        by_range('time', :chunk_interval)
                    );
                    """
                )
                .bindparams(sa.bindparam("chunk_interval", type_=Interval()))
                .params(chunk_interval=timedelta(days=1))
            )

        # If event_losses table is in new_metadata, add hypertable
        if f"{schema}.event_losses" in new_metadata.tables.keys():
            await db.execute(
                sa.text(
                    f"""
                    SELECT create_hypertable(
                        '{schema}.event_losses',
                        by_range('time')
                    );
                    """
                ),
            )

        logger.info(f"Successfully created schema and tables for project: {schema}")

    except Exception as e:
        logger.error(f"Failed to create schema and tables for project {schema}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create schema and tables: {e}"
        )


async def _get_elevation(
    *,
    latitude: float,
    longitude: float,
) -> float | None:
    """Get elevation from latitude and longitude using Open-Elevation API.

    Args:
        latitude: TODO: describe.
        longitude: TODO: describe.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.open-elevation.com/api/v1/lookup?locations={latitude},{longitude}"
            )
            response.raise_for_status()
            data = response.json()
            return float(data["results"][0]["elevation"])
        except httpx.RequestError as e:
            logger.error(f"Failed to get elevation: {e}")
            return None


def _get_timezone(*, latitude: float, longitude: float, **kwargs) -> str | None:
    """Get timezone from latitude and longitude using timezonefinder.

    Args:
        latitude: TODO: describe.
        longitude: TODO: describe.
        **kwargs: TODO: describe.
    """
    tf = TimezoneFinder()
    return tf.timezone_at(lng=longitude, lat=latitude)


async def create_project(
    *,
    db: AsyncSession,
    project_in: ProjectCreate,
    user_id: str,
    company_id: uuid.UUID,
) -> Project:
    """
    Creates a new project record in the database from the input data.
    Default values are set by the sqlalchemy model.
    Assigns the newly created project to:
    1. The user who created it
    2. All admins in the creator's company
    3. All superadmins regardless of company

    Args:
        db: The SQLAlchemy database session.
        project_in: The Pydantic model containing the project data.
        user_id: The ID of the user creating the project.
        company_id: The company ID of the user creating the project.

    Returns:
        The newly created database Project object.
    """
    # Get the input data
    project_data = project_in.model_dump()

    # Add required fields that aren't in ProjectCreate or have no model defaults
    project_data.update(
        {
            "project_id": uuid.uuid4(),
            "project_status_type_id": ProjectStatusType.ONBOARDING,
            "name_short": project_data["name_long"]
            .lower()
            .replace(
                " ", "_"
            ),  # Generate short name from long name (lowercase with underscores)
            "data_table": "data_timeseries",
            "data_interval": ProjectDataInterval.MQTT,
        }
    )

    # Convert latitude and longitude to Point geometry
    if "latitude" in project_data and "longitude" in project_data:
        lat = project_data.pop("latitude")
        lng = project_data.pop("longitude")
        if lat is not None and lng is not None:
            project_data["point"] = Point(lng, lat).wkt  ## well known text
            project_data["elevation"] = await _get_elevation(
                latitude=lat, longitude=lng
            )
            project_data["time_zone"] = _get_timezone(latitude=lat, longitude=lng)

    # Set defaults for optional capacity fields if not provided
    if project_data.get("capacity_dc") is None:
        project_data["capacity_dc"] = 0.0
    if project_data.get("capacity_ac") is None:
        project_data["capacity_ac"] = 0.0
    if project_data.get("capacity_bess_power_ac") is None:
        project_data["capacity_bess_power_ac"] = 0.0
    if project_data.get("capacity_bess_energy_bol_dc") is None:
        project_data["capacity_bess_energy_bol_dc"] = 0.0

    # --- ATOMIC TRANSACTION: All operations succeed or all fail ---
    try:
        # Create the project record using insert() with explicit column selection
        # to exclude project_id_int, allowing the database server_default to handle it
        # Get all columns except project_id_int
        columns_to_insert = {
            key: value for key, value in project_data.items() if key != "project_id_int"
        }

        result = await db.execute(
            sa.insert(DBProject).values(**columns_to_insert).returning(DBProject)
        )
        db_project = result.scalar_one()

        # Make project available for foreign key references without committing
        await db.flush()
        logger.info(f"Created project with ID: {db_project.project_id}")

        # Assign the project to creator, company admins, and all superadmins
        await assign_project_to_relevant_users(
            db=db,
            creator_user_id=user_id,
            creator_company_id=company_id,
            project_id=db_project.project_id,
            do_commit=False,
        )

        # Create Schema and Tables
        await _create_schema_and_tables(
            db=db,
            name_short=db_project.name_short,
            do_commit=False,
        )

        # Commit all operations together
        project_id_for_logs = str(db_project.project_id)
        await db.commit()
        logger.info(
            f"Successfully completed all operations for project: {project_id_for_logs}"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create project atomically: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")

    # Refresh to get the committed state
    await db.refresh(db_project)

    # --- Send gchat notification (outside transaction as it's not critical) ---
    # Get user and company names for notification
    user_name = str(user_id)  # fallback to ID
    company_name = str(company_id)  # fallback to ID

    try:
        user = await get_user(db=db, user_id=user_id)
        if user and user.name_long:
            user_name = user.name_long
    except Exception as e:
        logger.warning(f"Failed to get user name for notification: {e}")

    try:
        companies = await get_companies(db=db, company_ids=[company_id])
        if companies and companies[0].name_long:
            company_name = companies[0].name_long
    except Exception as e:
        logger.warning(f"Failed to get company name for notification: {e}")

    # Send notification to Google Chat
    try:
        send_project_creation_notification(
            project_name=db_project.name_short,
            created_by=user_name,
            created_by_company=company_name,
            channel=CommunicationChannel.GOOGLE_CHAT,
        )
    except Exception as e:
        # Log the error but don't fail the project creation
        logger.error(f"Failed to send project creation notification: {e}")

    # Convert the database object to the response format using from_attributes
    return Project.model_validate(db_project)
