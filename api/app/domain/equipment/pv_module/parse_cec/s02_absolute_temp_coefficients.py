from fastapi import HTTPException


def calc_cec_absolute_temp_coefficients(
    *,
    cec_pv_module: dict,
) -> dict:
    """Calculate the absolute temperature coefficients for a PV module if they are not
        provided.

    Args:
        cec_pv_module: Description for cec_pv_module.
    """
    # --- Quality Control of Current Temperature Coefficients ---
    if (cec_pv_module.get("alpha_isc") is None) & (
        cec_pv_module.get("alpha_isc_relative") is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Either alpha_isc or alpha_isc_relative must be not None",
        )
    elif (cec_pv_module.get("alpha_isc") is not None) & (
        cec_pv_module.get("alpha_isc_relative") is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Only one of alpha_isc or alpha_isc_relative must be not None",
        )
    else:
        pass

    # --- Quality Control of Voltage Temperature Coefficients ---
    if (cec_pv_module.get("beta_voc") is None) & (
        cec_pv_module.get("beta_voc_relative") is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Either beta_voc or beta_voc_relative must be not None",
        )
    elif (cec_pv_module.get("beta_voc") is not None) & (
        cec_pv_module.get("beta_voc_relative") is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="Only one of beta_voc or beta_voc_relative must be not None",
        )
    else:
        pass

    # --- Convert Relative to Absolute ---
    if (cec_pv_module.get("alpha_isc_relative") is not None) & (
        cec_pv_module.get("alpha_isc") is None
    ):
        isc = cec_pv_module.get("isc")
        alpha_isc_relative = cec_pv_module.get("alpha_isc_relative")
        if isc is not None and alpha_isc_relative is not None:
            cec_pv_module["alpha_isc"] = isc * alpha_isc_relative / 100.0
    else:
        pass

    if (cec_pv_module.get("beta_voc_relative") is not None) & (
        cec_pv_module.get("beta_voc") is None
    ):
        voc = cec_pv_module.get("voc")
        beta_voc_relative = cec_pv_module.get("beta_voc_relative")
        if voc is not None and beta_voc_relative is not None:
            cec_pv_module["beta_voc"] = voc * beta_voc_relative / 100.0
    else:
        pass

    return cec_pv_module
