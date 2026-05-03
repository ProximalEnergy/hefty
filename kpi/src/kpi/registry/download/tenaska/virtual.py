from kpi.op.download.tenaska import TenaskaModel, tenaska_field
from kpi.op.field_registry import FieldRegistry


class DownloadTenaskaVirtual(FieldRegistry[TenaskaModel]):
    virtual_real_time_energy_imbalance_raw_usd_15m = tenaska_field("RTEIAMT", scale=-1)

    virtual_day_ahead_energy_payment_raw_usd_15m = tenaska_field("DAESAMT", scale=-1)
