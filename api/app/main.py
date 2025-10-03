import warnings

warnings.simplefilter("always", DeprecationWarning)

import tomllib

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from app import settings
from app.logger import logger
from app.v1 import v1

if settings.ENVIRONMENT in ["staging", "production"]:
    sentry_config = {
        "staging": {
            "traces_sample_rate": 0.5,
            "profiles_sample_rate": 0.5,
        },
        "production": {
            "traces_sample_rate": 0.1,
            "profiles_sample_rate": 0.2,
        },
    }
    sentry_sdk.init(
        dsn="https://4bb149534df11fb24f1ab6e8d61650b7@o4506555874672640.ingest.sentry.io/4506555876442112",
        traces_sample_rate=sentry_config[settings.ENVIRONMENT]["traces_sample_rate"],
        profiles_sample_rate=sentry_config[settings.ENVIRONMENT][
            "profiles_sample_rate"
        ],
        environment=settings.ENVIRONMENT,
    )
else:
    logger.warning("Sentry is not enabled for this environment")

with open("pyproject.toml", "rb") as f:  # Note: must open in binary mode
    api_meta_data = tomllib.load(f)
version = api_meta_data["project"]["version"]
app = FastAPI(
    title="Proximal Energy API",
    description="Documentation for the Proximal Energy API",
    version=version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.proximal.energy",  # Production
        "https://staging.d1waz5kiczd3n9.amplifyapp.com",  # Staging
        "http://localhost:5173",  # Local development
        "https://main.diyg9kphy7rh8.amplifyapp.com",  # Mono Repo Prod
        "https://staging.diyg9kphy7rh8.amplifyapp.com",  # Mono Repo Staging
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1.router)

mcp = FastApiMCP(
    app,
    name="proximal-api",
    include_operations=[
        "get_sensor_type",
        "get_sensor_types",
        "get_device_types",
        "get_device_statuses",
        "get_device_status_binary",
        "get_report_type_by_id",
        "get_report_types",
        "get_root_causes",
        "get_kpi_types",
        "get_kpi_type_by_id",
        "get_kpi_type_by_name",
        "get_kpi_types_by_project",
        "get_project_types",
        "get_project_type_by_id",
        "get_projects",
        "get_project_by_id",
        "get_project_data_last_updated",
        "get_report_instances",
        "get_report_instance_by_id",
        "get_inverters",
        "get_inverter_by_id",
        "get_inverter_ids",
        "get_proximal_inverter_manufacturers",
        "get_proximal_inverter_models_given_manufacturer",
        "get_inverter_ids_by_manufacturer_and_model",
        "get_project_devices",
        "get_project_devices_v2",
        "get_project_devices_v2_example",
        "get_project_device_by_id",
        "get_project_contracts",
        "get_project_contract_kpis",
    ],
    include_tags=["sensor_types"],
    headers=["x-api-key"],
)
mcp.mount()


@app.get("/")
def get_root():
    return "Proximal Energy API"


@app.get("/version")
def get_version():
    return {"version": version}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
