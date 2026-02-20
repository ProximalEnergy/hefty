from dataclasses import dataclass

import pvlib
from interfaces import Indeces, MetTimeSeries, TimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension


@dataclass(init=False, slots=True)
class DHI:
    """DHI."""

    dhi: MetTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        zenith: TimeSeries,
        ghi: MetTimeSeries,
        dni: MetTimeSeries,
    ):
        # --- merge ---
        inputs = merge_by_dimension(
            data_series=[
                zenith,
                ghi,
                dni,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- Calculate DHI ---
        dhi = pvlib.irradiance.complete_irradiance(
            solar_zenith=inputs["zenith"],  # not refraction corrected
            ghi=inputs["ghi"],
            dni=inputs["dni"],
            dhi=None,
        ).loc[:, "dhi"]

        self.dhi = MetTimeSeries(dhi)
