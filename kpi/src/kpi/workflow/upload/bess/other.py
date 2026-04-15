from core.enumerations import KPIType
from kpi.service.upload import UploadModel, UploadSchema
from kpi.workflow.transform.bess.summarize.workflow import TransformBessSummarize

T = TransformBessSummarize

models: list[UploadModel] = [
    # =======================================================
    # Bank
    # =======================================================
    UploadModel(
        kpi_type=KPIType.BESS_BANK_AVERAGE_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_bank_soc_d.name,
        device_var=T.bank_avg_soc_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BANK_RESTING_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_bank_resting_soc_d.name,
        device_var=T.bank_avg_resting_soc_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BANK_CYCLE_COUNT,
        version="2.0.0",
        project_var=T.project_avg_bank_cycle_count_d.name,
        device_var=T.bank_cycle_count_d.name,
    ),
    # BESS_BANK_ENERGY_CHARGED (36) not implemented
    # BESS_BANK_ENERGY_DISCHARGED (40) not implemented
    # BESS_BANK_RTE (44) not implemented
    UploadModel(
        kpi_type=KPIType.BESS_BANK_DEPTH_OF_DISCHARGE,
        version="2.0.0",
        project_var=T.project_avg_bank_dod_d.name,
        device_var=T.bank_avg_dod_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BANK_SOH,
        version="2.0.0",
        project_var=T.project_bank_soh_d.name,
        device_var=T.bank_soh_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BANK_AVAILABILITY,
        version="2.0.0",
        project_var=T.project_bank_availability_d.name,
        device_var=T.bank_availability_d.name,
    ),
    # =======================================================
    # Block
    # =======================================================
    UploadModel(
        kpi_type=KPIType.BESS_BLOCK_CYCLE_COUNT,
        version="2.0.0",
        project_var=T.project_avg_block_cycle_count_d.name,
        device_var=T.block_cycle_count_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BLOCK_RESTING_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_block_resting_soc_d.name,
        device_var=T.block_avg_resting_soc_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_BLOCK_AVERAGE_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_block_soc_d.name,
        device_var=T.block_avg_soc_d.name,
    ),
    # =======================================================
    # DC enclosure
    # =======================================================
    # BESS_DC_ENCLOSURE_AVERAGE_SOC_PERCENT (26) not implemented
    # BESS_DC_ENCLOSURE_RESTING_SOC_PERCENT (27) not implemented
    # BESS_DC_ENCLOSURE_CYCLE_COUNT (28) not implemented
    # =======================================================
    # Circuit
    # =======================================================
    UploadModel(
        kpi_type=KPIType.BESS_CIRCUIT_ENERGY_CHARGED,
        version="2.0.0",
        project_var=T.project_circuit_energy_charged_kwh_d.name,
        device_var=T.circuit_energy_charged_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_CIRCUIT_ENERGY_DISCHARGED,
        version="2.0.0",
        project_var=T.project_circuit_energy_discharged_kwh_d.name,
        device_var=T.circuit_energy_discharged_kwh_d.name,
        scale=0.001,
    ),
    # =======================================================
    # BESS module
    # =======================================================
    # BESS_MODULE_ENERGY_CHARGED (38) not implemented
    # BESS_MODULE_ENERGY_DISCHARGED (42) not implemented
    # BESS_MODULE_RTE (46) not implemented
    # BESS_MODULE_DEPTH_OF_DISCHARGE (50) not implemented
    # BESS_MODULE_SOH (55) not implemented
    # =======================================================
    # PCS module
    # =======================================================
    UploadModel(
        kpi_type=KPIType.BESS_PCS_MODULE_AVAILABILITY,
        version="2.0.1",
        project_var=T.project_pcs_module_availability_d.name,
        device_var=T.pcs_module_availability_d.name,
    ),
    # BESS_PCS_MODULE_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (110) not implemented
    UploadModel(
        kpi_type=KPIType.BESS_PCS_MODULE_ENERGY_CHARGED,
        version="2.0.0",
        project_var=T.project_pcs_module_energy_charged_kwh_d.name,
        device_var=T.pcs_module_energy_charged_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_MODULE_ENERGY_DISCHARGED,
        version="2.0.0",
        project_var=T.project_pcs_module_energy_discharged_kwh_d.name,
        device_var=T.pcs_module_energy_discharged_kwh_d.name,
        scale=0.001,
    ),
]

registry = {model.kpi_type.name: model for model in models}


class UploadBessOther(UploadSchema):
    """Registry of non-project BESS KPI fields for upload."""

    _field_registry = registry
