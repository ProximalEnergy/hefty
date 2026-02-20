import logging
from dataclasses import dataclass
from enum import Enum

import boto3
import pandas as pd
import polars as pl
import s3fs
from interfaces import (
    InverterDeviceSeries,
    SystemSeries,
    TransformerDeviceSeries,
)


class RackingControlsAlgorithm(Enum):
    """RackingControlsAlgorithm."""

    FIXED = 0
    TRUE_TRACKING_2D = 1
    BACK_TRACKING_2D = 2


@dataclass(slots=True)
class System:
    """System."""

    string_id: SystemSeries
    module_equipment_id: SystemSeries
    modules_per_string: SystemSeries
    strings_per_combiner: SystemSeries
    dc_line_to_combiner_stc: SystemSeries
    combiner_device_id: SystemSeries
    pitch: SystemSeries
    racking_controls_gcr: SystemSeries
    racking_equipment_id: SystemSeries
    racking_controls_algorithm: SystemSeries  # categorical
    racking_device_id: SystemSeries
    dc_line_to_inverter_stc: SystemSeries
    pcs_equipment_id: InverterDeviceSeries
    pcs_device_id: InverterDeviceSeries
    transformer_equipment_id: TransformerDeviceSeries
    transformer_device_id: TransformerDeviceSeries
    block_device_id: SystemSeries
    circuit_device_id: SystemSeries
    met_name: SystemSeries

    @classmethod
    async def create(
        cls,
        project_name_short: str,
        AWS_S3_BUCKET_NAME: str,
    ):
        """Get system mechanical and electrical components
        Args:
            * project_name_short:  name_short in the project
        """
        # --- Authenticate with S3 ---
        # This will look in a few different places:
        # 1. Local .env file
        # 2. Docker Container with volume mounted:  ~/.aws:/root/.aws
        # 3. IAM role in Github Actions
        fs = s3fs.S3FileSystem(asynchronous=False)

        # --- Check read from S3 ---
        try:
            with fs.open(
                f"{AWS_S3_BUCKET_NAME}/{project_name_short}.parquet", "rb"
            ) as f:
                system = pl.read_parquet(f)
        except FileNotFoundError:
            logging.critical(f"File not found: {project_name_short}.parquet")
            system = pl.DataFrame()
        except PermissionError as pe:
            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
            logging.info(f"Lambda execution role: {identity['Arn']}")
            logging.critical(f"... Permission Error: {pe}")
            system = pl.DataFrame()

        # --- QC ---
        match system.is_empty():
            case True:
                logging.critical("System data is empty")
                raise ValueError("System data is empty")
            case False:
                system_pandas: pd.DataFrame = system.to_pandas()

        return cls(
            string_id=SystemSeries(system_pandas.loc[:, "string_id"]),
            module_equipment_id=SystemSeries(
                system_pandas.loc[:, "module_equipment_id"]
            ),
            modules_per_string=SystemSeries(system_pandas.loc[:, "modules_per_string"]),
            strings_per_combiner=SystemSeries(
                system_pandas.loc[:, "strings_per_combiner"]
            ),
            dc_line_to_combiner_stc=SystemSeries(
                system_pandas.loc[:, "dc_line_to_combiner_stc"]
            ),
            combiner_device_id=SystemSeries(system_pandas.loc[:, "combiner_device_id"]),
            racking_controls_gcr=SystemSeries(
                system_pandas.loc[:, "racking_controls_gcr"]
            ),
            racking_equipment_id=SystemSeries(
                system_pandas.loc[:, "racking_equipment_id"]
            ),
            racking_device_id=SystemSeries(system_pandas.loc[:, "racking_device_id"]),
            dc_line_to_inverter_stc=SystemSeries(
                system_pandas.loc[:, "dc_line_to_inverter_stc"]
            ),
            pcs_equipment_id=InverterDeviceSeries(
                system_pandas.loc[:, "pcs_equipment_id"]
            ),
            pcs_device_id=InverterDeviceSeries(system_pandas.loc[:, "pcs_device_id"]),
            transformer_equipment_id=TransformerDeviceSeries(
                system_pandas.loc[:, "transformer_equipment_id"]
            ),
            transformer_device_id=TransformerDeviceSeries(
                system_pandas.loc[:, "transformer_device_id"]
            ),
            block_device_id=SystemSeries(system_pandas.loc[:, "block_device_id"]),
            circuit_device_id=SystemSeries(system_pandas.loc[:, "circuit_device_id"]),
            met_name=SystemSeries(system_pandas.loc[:, "met_name"]),
            #
            # --- computed later ---
            #
            racking_controls_algorithm=SystemSeries(pd.Series()),
            pitch=SystemSeries(pd.Series()),
        )
