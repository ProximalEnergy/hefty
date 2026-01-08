import datetime
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app._crud.operational.drone_integrations import (
    get_drone_integration_by_project_id,
)
from app._crud.projects.drone_anomalies import (
    bulk_create_drone_anomalies_incremental,
    get_anomalies_by_inspection_uuid,
    get_anomaly_count_by_inspection_uuid,
)
from app._crud.projects.drone_inspections import (
    create_drone_inspection,
    get_drone_inspections,
)
from app._dependencies.authorization import require_jwt_or_api_superadmin
from app.dependencies import get_async_db, get_project_db
from app.domain.drones.zeitview_parser import ZeitviewAPI
from app.interfaces import (
    DroneAnomaly,
    DroneAnomalyCreate,
    DroneInspection,
    DroneInspectionCreate,
    ZeitviewInspection,
)
from app.logger import logger

router = APIRouter(
    prefix="/projects/{project_id}/drone-inspections",
    tags=["project_drone_inspections"],
    dependencies=[Depends(require_jwt_or_api_superadmin)],
)


@router.get("", response_model=list[DroneInspection])
def get_db_inspections(
    project_id: uuid.UUID,
    db: Session = Depends(get_project_db),
):
    """Get a list of historical inspections from the database for a given project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
    """
    try:
        inspections = get_drone_inspections(db=db)
        return inspections
    except ValueError as e:
        logger.error(f"Error getting inspections from db for project {project_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error fetching inspections from db for project "
            f"{project_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get(
    "/zeitview",
    response_model=list[ZeitviewInspection],
)
async def get_zeitview_inspections(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    project_db: Session = Depends(get_project_db),
):
    """Get a list of historical inspections from Zeitview for a given project.

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
    """
    integration = await get_drone_integration_by_project_id(
        db=db, project_id=project_id
    )

    if not integration:
        raise HTTPException(
            status_code=404,
            detail="No drone integration found for this project.",
        )

    try:
        zeitview_api = ZeitviewAPI(
            drone_integration_id=integration.drone_integration_id
        )
        inspections_data = await zeitview_api.query_site_inspections(
            site_uuid=integration.provider_project_id
        )
        # The API returns a dictionary, and we are interested in the 'data' list
        parsed_inspections = [
            ZeitviewInspection(**item) for item in inspections_data.get("data", [])
        ]

        for inspection in parsed_inspections:
            # Convert string dates to datetime objects
            inspection_datetime = datetime.datetime.fromisoformat(
                inspection.inspection_date.replace("Z", "+00:00")
            )
            upload_datetime = datetime.datetime.fromisoformat(
                inspection.upload_date.replace("Z", "+00:00")
            )

            inspection_create = DroneInspectionCreate(
                inspection_uuid=inspection.inspection_uuid,
                inspection_time=inspection_datetime,
                upload_time=upload_datetime,
                service_tier=inspection.service_tier,
                total_power_loss_kw=inspection.total_power_loss_kw,
                total_power_loss_percent=inspection.total_power_loss_percent,
                total_affected_modules=inspection.total_affected_modules,
                report_summary=inspection.report_summary,
            )
            create_drone_inspection(db=project_db, inspection_data=inspection_create)

        return parsed_inspections
    except ValueError as e:
        # This catches errors from ZeitviewAPI init (e.g., missing secret)
        logger.error(f"Error initializing ZeitviewAPI for project {project_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch other potential exceptions from the API call
        logger.error(
            f"Unexpected error fetching inspections for project {project_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@router.get(
    "/{inspection_uuid}/anomalies",
    response_model=list[DroneAnomaly],
)
def get_db_anomalies(
    inspection_uuid: uuid.UUID,
    db: Session = Depends(get_project_db),
):
    """Get a list of anomalies from the database for a given inspection.

    Args:
        inspection_uuid: TODO: describe.
        db: TODO: describe.
    """
    try:
        anomalies = get_anomalies_by_inspection_uuid(
            db=db, inspection_uuid=inspection_uuid
        )
        return anomalies
    except ValueError as e:
        logger.error(
            f"Error getting anomalies from db for inspection {inspection_uuid}: {e}"
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error fetching anomalies from db for inspection "
            f"{inspection_uuid}: {e}"
        )
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.post(
    "/{inspection_uuid}/anomalies/zeitview",
    response_model=dict,
)
async def sync_zeitview_anomalies(
    project_id: uuid.UUID,
    inspection_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    project_db: Session = Depends(get_project_db),
):
    """Fetch anomalies from Zeitview and store them in the database
    incrementally. Can resume from where it left off if interrupted.

    Args:
        project_id: TODO: describe.
        inspection_uuid: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
    """
    integration = await get_drone_integration_by_project_id(
        db=db, project_id=project_id
    )
    if not integration:
        raise HTTPException(
            status_code=404,
            detail="No drone integration found for this project.",
        )

    try:
        # Check how many anomalies we already have
        existing_count = get_anomaly_count_by_inspection_uuid(
            db=project_db, inspection_uuid=inspection_uuid
        )

        # Calculate starting page and offset within that page
        page_size = 200
        start_page = (existing_count // page_size) + 1
        offset_within_page = (
            existing_count % page_size
        )  # How many anomalies we already have from the starting page

        logger.info(
            "Starting sync from page "
            f"{start_page} with offset {offset_within_page} "
            f"(existing anomalies: {existing_count})"
        )

        zeitview_api = ZeitviewAPI(
            drone_integration_id=integration.drone_integration_id
        )

        total_synced = 0
        is_first_page = True

        async def process_page(anomalies: list, page: int):
            """Process a single page of anomalies and insert them into the database

            Args:
                anomalies: TODO: describe.
                page: TODO: describe.
            """
            nonlocal total_synced, is_first_page

            if not anomalies:
                return

            # For the first page, skip anomalies we already have
            if is_first_page and offset_within_page > 0:
                anomalies = anomalies[offset_within_page:]
                logger.info(
                    "Skipping first "
                    f"{offset_within_page} anomalies from page {page}, "
                    f"processing {len(anomalies)} new ones"
                )
                is_first_page = False

            if not anomalies:
                is_first_page = False
                return

            anomalies_to_create = []
            for item in anomalies:
                # Handle location field - GeoJSON Point format with
                # coordinates [lon, lat]
                location = item.pop("location", {})
                if isinstance(location, str):
                    try:
                        location = json.loads(location)
                    except (json.JSONDecodeError, TypeError):
                        location = {}

                # Extract coordinates from GeoJSON Point format
                if isinstance(location, dict) and location.get("type") == "Point":
                    coordinates = location.get("coordinates", [])
                    if isinstance(coordinates, list) and len(coordinates) >= 2:
                        item["location_lon"] = coordinates[0]  # longitude first
                        item["location_lat"] = coordinates[1]  # latitude second
                    else:
                        item["location_lat"] = None
                        item["location_lon"] = None
                else:
                    item["location_lat"] = None
                    item["location_lon"] = None

                # Extract image URLs from the images field
                raw_images = item.pop("images", {})
                if isinstance(raw_images, dict):
                    # Fix URL encoding where Zeitview returns "%2520" so they
                    # become usable ("%20")
                    def _fix_url(*, url: str | None) -> str | None:
                        """todo

                        Args:
                            url: TODO: describe.
                        """
                        if not isinstance(url, str):
                            return url
                        return url.replace("%25", "%")

                    item["ir_image_url"] = _fix_url(url=raw_images.get("ir_image"))
                    item["rgb_image_url"] = _fix_url(url=raw_images.get("rgb_image"))
                else:
                    item["ir_image_url"] = None
                    item["rgb_image_url"] = None

                # Handle ir_signal and rgb_signal (they might not be in the API
                # response when not explicitly requested)
                if "ir_signal" not in item:
                    item["ir_signal"] = None
                if "rgb_signal" not in item:
                    item["rgb_signal"] = None

                # Since the API doesn't provide a UUID for the anomaly, we create one.
                item["anomaly_uuid"] = uuid.uuid4()
                item["inspection_uuid"] = inspection_uuid

                anomalies_to_create.append(DroneAnomalyCreate(**item))

            if anomalies_to_create:
                bulk_create_drone_anomalies_incremental(
                    db=project_db,
                    anomalies_data=anomalies_to_create,
                    inspection_uuid=inspection_uuid,
                )
                total_synced += len(anomalies_to_create)
                logger.info(
                    f"Inserted {len(anomalies_to_create)} anomalies from page {page}"
                )

            is_first_page = False

        # Query anomalies with page callback for incremental processing
        await zeitview_api.query_inspection_anomalies(
            inspection_uuid=str(inspection_uuid),
            start_page=start_page,
            page_callback=process_page,
        )

        return {
            "status": "success",
            "synced_anomalies": total_synced,
            "started_from_page": start_page,
            "existing_anomalies": existing_count,
        }

    except ValueError as e:
        logger.error(f"Error initializing ZeitviewAPI for project {project_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error fetching anomalies for inspection {inspection_uuid}: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )
