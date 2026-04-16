import logging
from dataclasses import dataclass

import pandas as pd
import polars as pl
from core.db_query import DbQuery, OutputType
from interfaces import ModuleEquipmentSeries
from sqlalchemy import bindparam, text


@dataclass(slots=True)
class Module:
    # Basic module information
    """Module."""

    module_equipment_id: ModuleEquipmentSeries
    company_id: ModuleEquipmentSeries
    manufacturer: ModuleEquipmentSeries
    model: ModuleEquipmentSeries
    family: ModuleEquipmentSeries
    technology: ModuleEquipmentSeries
    bifaciality_factor: ModuleEquipmentSeries

    # Electrical characteristics
    pmax: ModuleEquipmentSeries
    isc: ModuleEquipmentSeries
    voc: ModuleEquipmentSeries
    imp: ModuleEquipmentSeries
    vmp: ModuleEquipmentSeries
    efficiency: ModuleEquipmentSeries  # calculated

    # Temperature coefficients
    gamma_pmax: ModuleEquipmentSeries
    alpha_isc: ModuleEquipmentSeries
    beta_voc: ModuleEquipmentSeries

    # Degradation parameters
    warranted_degradation_rate: ModuleEquipmentSeries
    warranted_degradation_initial: ModuleEquipmentSeries

    # Physical dimensions
    length: ModuleEquipmentSeries
    width: ModuleEquipmentSeries
    area: ModuleEquipmentSeries  # calculated
    frame_overhang: ModuleEquipmentSeries

    # Module characteristics
    has_ar_coating: ModuleEquipmentSeries
    half_cut: ModuleEquipmentSeries
    cells_in_series: ModuleEquipmentSeries

    # Single diode model parameters
    photocurrent: ModuleEquipmentSeries
    diode_saturation_current: ModuleEquipmentSeries
    r_series: ModuleEquipmentSeries
    r_shunt: ModuleEquipmentSeries
    r_shunt_0: ModuleEquipmentSeries
    r_shunt_exponent: ModuleEquipmentSeries
    diode_ideality_factor: ModuleEquipmentSeries
    diode_ideality_factor_temp_coefficient: ModuleEquipmentSeries
    modified_ideality_factor: ModuleEquipmentSeries
    eg: ModuleEquipmentSeries
    degdt: ModuleEquipmentSeries

    # Data source
    data_source: ModuleEquipmentSeries

    @classmethod
    async def get_module_data(
        cls,
        *,
        unique_module_ids: pd.Series,
    ) -> "Module":
        """Get all of the relevant module data from the pv_modules table
        Args:
            * unique_module_ids:  polars dataframe column filtered for
            unique module ids
        """
        module_query = text(
            """
            SELECT
                pv_module_id,
                company_id,
                manufacturer,
                model,
                family,
                technology,
                bifaciality_factor,
                pmax,
                isc,
                voc,
                imp,
                vmp,
                gamma_pmax,
                alpha_isc,
                beta_voc,
                warranted_degradation_rate,
                warranted_degradation_initial,
                length,
                width,
                frame_overhang,
                has_ar_coating,
                half_cut,
                cells_in_series,
                photocurrent,
                diode_saturation_current,
                r_series,
                r_shunt,
                r_shunt_0,
                r_shunt_exponent,
                diode_ideality_factor,
                diode_ideality_factor_temp_coefficient,
                modified_ideality_factor,
                eg,
                degdt,
                data_source
            FROM operational.pv_modules
            WHERE pv_module_id IN :module_ids
        """
        ).bindparams(
            bindparam(
                "module_ids",
                value=unique_module_ids.tolist(),
                expanding=True,
            )
        )

        modules: pl.DataFrame = await DbQuery(query=module_query).get_async(
            schema=None,
            output_type=OutputType.POLARS,
        )
        modules_pd = modules.to_pandas()

        if modules_pd.empty:
            logging.critical("No module found for project")
            raise ValueError("No module found for project")

        # Renaming
        modules_pd = modules_pd.rename(columns={"pv_module_id": "module_equipment_id"})

        # Calculations (TO DO:  Move these to the DB)
        modules_pd["area"] = modules_pd["length"] * modules_pd["width"]
        modules_pd["efficiency"] = modules_pd["pmax"] / (modules_pd["area"] * 1000.0)

        return cls(
            module_equipment_id=ModuleEquipmentSeries(
                modules_pd.loc[:, "module_equipment_id"]
            ),
            company_id=ModuleEquipmentSeries(modules_pd.loc[:, "company_id"]),
            manufacturer=ModuleEquipmentSeries(modules_pd.loc[:, "manufacturer"]),
            model=ModuleEquipmentSeries(modules_pd.loc[:, "model"]),
            family=ModuleEquipmentSeries(modules_pd.loc[:, "family"]),
            technology=ModuleEquipmentSeries(modules_pd.loc[:, "technology"]),
            bifaciality_factor=ModuleEquipmentSeries(
                modules_pd.loc[:, "bifaciality_factor"]
            ),
            pmax=ModuleEquipmentSeries(
                modules_pd.loc[:, "pmax"].rename("module_p_max_stc")
            ),
            isc=ModuleEquipmentSeries(
                modules_pd.loc[:, "isc"].rename("module_i_sc_stc")
            ),
            voc=ModuleEquipmentSeries(
                modules_pd.loc[:, "voc"].rename("module_v_oc_stc")
            ),
            imp=ModuleEquipmentSeries(
                modules_pd.loc[:, "imp"].rename("module_i_mp_stc")
            ),
            vmp=ModuleEquipmentSeries(
                modules_pd.loc[:, "vmp"].rename("module_v_mp_stc")
            ),
            efficiency=ModuleEquipmentSeries(modules_pd.loc[:, "efficiency"]),
            gamma_pmax=ModuleEquipmentSeries(modules_pd.loc[:, "gamma_pmax"]),
            alpha_isc=ModuleEquipmentSeries(modules_pd.loc[:, "alpha_isc"]),
            beta_voc=ModuleEquipmentSeries(modules_pd.loc[:, "beta_voc"]),
            warranted_degradation_rate=ModuleEquipmentSeries(
                modules_pd.loc[:, "warranted_degradation_rate"]
            ),
            warranted_degradation_initial=ModuleEquipmentSeries(
                modules_pd.loc[:, "warranted_degradation_initial"]
            ),
            length=ModuleEquipmentSeries(modules_pd.loc[:, "length"]),
            width=ModuleEquipmentSeries(modules_pd.loc[:, "width"]),
            area=ModuleEquipmentSeries(modules_pd.loc[:, "area"]),
            frame_overhang=ModuleEquipmentSeries(modules_pd.loc[:, "frame_overhang"]),
            has_ar_coating=ModuleEquipmentSeries(modules_pd.loc[:, "has_ar_coating"]),
            half_cut=ModuleEquipmentSeries(modules_pd.loc[:, "half_cut"]),
            cells_in_series=ModuleEquipmentSeries(modules_pd.loc[:, "cells_in_series"]),
            photocurrent=ModuleEquipmentSeries(modules_pd.loc[:, "photocurrent"]),
            diode_saturation_current=ModuleEquipmentSeries(
                modules_pd.loc[:, "diode_saturation_current"]
            ),
            r_series=ModuleEquipmentSeries(modules_pd.loc[:, "r_series"]),
            r_shunt=ModuleEquipmentSeries(modules_pd.loc[:, "r_shunt"]),
            r_shunt_0=ModuleEquipmentSeries(modules_pd.loc[:, "r_shunt_0"]),
            r_shunt_exponent=ModuleEquipmentSeries(
                modules_pd.loc[:, "r_shunt_exponent"]
            ),
            diode_ideality_factor=ModuleEquipmentSeries(
                modules_pd.loc[:, "diode_ideality_factor"]
            ),
            diode_ideality_factor_temp_coefficient=ModuleEquipmentSeries(
                modules_pd.loc[:, "diode_ideality_factor_temp_coefficient"]
            ),
            modified_ideality_factor=ModuleEquipmentSeries(
                modules_pd.loc[:, "modified_ideality_factor"]
            ),
            eg=ModuleEquipmentSeries(modules_pd.loc[:, "eg"]),
            degdt=ModuleEquipmentSeries(modules_pd.loc[:, "degdt"]),
            data_source=ModuleEquipmentSeries(modules_pd.loc[:, "data_source"]),
        )
