from core.enumerations import KPITypeEnum
from kpi.op.upload import UploadModel
from kpi.registry.transform.bess.summarize.api import (
    TransformBessSummarize as Summarize,
)

models: list[UploadModel] = [
    # =======================================================
    # Bank
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_AVERAGE_SOC_PERCENT,
        version="2.0.0",
        project_var=Summarize.project_avg_bank_soc_d,
        device_var=Summarize.bank_avg_soc_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_RESTING_SOC_PERCENT,
        version="2.0.0",
        project_var=Summarize.project_avg_bank_resting_soc_d,
        device_var=Summarize.bank_avg_resting_soc_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_CYCLE_COUNT,
        version="2.0.0",
        project_var=Summarize.project_avg_bank_cycle_count_d,
        device_var=Summarize.bank_cycle_count_d,
    ),
    # BESS_BANK_ENERGY_CHARGED (36) not implemented
    # BESS_BANK_ENERGY_DISCHARGED (40) not implemented
    # BESS_BANK_RTE (44) not implemented
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_DEPTH_OF_DISCHARGE,
        version="2.0.0",
        project_var=Summarize.project_avg_bank_dod_d,
        device_var=Summarize.bank_avg_dod_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_SOH,
        version="2.0.0",
        project_var=Summarize.project_bank_soh_d,
        device_var=Summarize.bank_soh_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BANK_AVAILABILITY,
        version="2.0.0",
        project_var=Summarize.project_bank_availability_d,
        device_var=Summarize.bank_availability_d,
    ),
    # =======================================================
    # Block
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BLOCK_CYCLE_COUNT,
        version="2.0.0",
        project_var=Summarize.project_avg_block_cycle_count_d,
        device_var=Summarize.block_cycle_count_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BLOCK_RESTING_SOC_PERCENT,
        version="2.0.0",
        project_var=Summarize.project_avg_block_resting_soc_d,
        device_var=Summarize.block_avg_resting_soc_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_BLOCK_AVERAGE_SOC_PERCENT,
        version="2.0.0",
        project_var=Summarize.project_avg_block_soc_d,
        device_var=Summarize.block_avg_soc_d,
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
        kpi_type=KPITypeEnum.BESS_CIRCUIT_ENERGY_CHARGED,
        version="2.0.0",
        project_var=Summarize.project_circuit_energy_charged_kwh_d,
        device_var=Summarize.circuit_energy_charged_kwh_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_CIRCUIT_ENERGY_DISCHARGED,
        version="2.0.0",
        project_var=Summarize.project_circuit_energy_discharged_kwh_d,
        device_var=Summarize.circuit_energy_discharged_kwh_d,
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
        kpi_type=KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY,
        version="2.0.1",
        project_var=Summarize.project_pcs_module_availability_d,
        device_var=Summarize.pcs_module_availability_d,
    ),
    # BESS_PCS_MODULE_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (110) not implemented
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_MODULE_ENERGY_CHARGED,
        version="2.0.0",
        project_var=Summarize.project_pcs_module_energy_charged_kwh_d,
        device_var=Summarize.pcs_module_energy_charged_kwh_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_MODULE_ENERGY_DISCHARGED,
        version="2.0.0",
        project_var=Summarize.project_pcs_module_energy_discharged_kwh_d,
        device_var=Summarize.pcs_module_energy_discharged_kwh_d,
        scale=0.001,
    ),
]

UPLOAD_BESS_OTHER: dict[str, UploadModel] = {
    model.kpi_type.name: model for model in models
}
