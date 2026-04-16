import math
from typing import Any, cast


def solve_stc_parameters(
    *,
    pv_module_data: dict[str, Any],
    pan_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Solves for Iph and Io at Standard Test Conditions (STC) using the
    mathematical synthesis. Generalizable to any module provided via a
    .pan file reader.

    Args:
        pv_module_data: Parsed module parameters used to solve STC values and
            updated in place with the calculated outputs.
        pan_data: Parsed `.pan` metadata used to read supplemental values such
            as `D2MuTau`.

    Returns:
        The updated module parameter mapping including the calculated single
        diode parameters.
    """

    # 1. Input Data
    def _get_param(*, keys: tuple[str, ...], source: dict[str, Any]) -> float:
        for k in keys:
            if k in source and source[k] is not None:
                return float(source[k])
        raise ValueError(f"Missing required parameter: {keys[0]}")

    isc = _get_param(keys=("isc", "Isc"), source=pv_module_data)
    voc = _get_param(keys=("voc", "Voc"), source=pv_module_data)
    rs = _get_param(keys=("r_series", "Rs"), source=pv_module_data)
    rsh = _get_param(keys=("r_shunt", "Rsh"), source=pv_module_data)
    gamma = _get_param(
        keys=("diode_ideality_factor", "Gamma"),
        source=pv_module_data,
    )
    cells_in_series = _get_param(
        keys=("cells_in_series", "NCelS"),
        source=pv_module_data,
    )

    d2mutau: object | None = pan_data.get("D2MuTau")
    pv_object = pan_data.get("PVObject_")
    if d2mutau in (None, "") and isinstance(pv_object, dict):
        d2mutau = pv_object.get("D2MuTau")

    if d2mutau in (None, ""):
        raise ValueError("Missing required parameter: D2MuTau")
    d2mutau = float(cast(str | float | int, d2mutau))

    # 2. Defined Constants
    v_t = 0.02569
    v_bi = 0.9

    # 3. Mathematical Synthesis Steps
    # Gamma in PAN is per-cell, while Voc is module-level.
    modified_ideality_factor = cells_in_series * gamma * v_t

    # Step 2: Formulate Short-Circuit Coefficients (at V=0, I=Isc)
    v_int_sc = isc * rs
    m_rec_sc = d2mutau / (v_bi - v_int_sc) if (v_bi - v_int_sc) != 0.0 else 0.0

    # Step 4: Solve the Linear System (isolate Iph)
    # The diode term at short-circuit is negligible, allowing for direct isolation
    if (1.0 - m_rec_sc) != 0.0:
        iph = (isc * (1.0 + (rs / rsh if rsh != 0.0 else 0.0))) / (1.0 - m_rec_sc)
    else:
        iph = 0.0

    # Step 3: Formulate Open-Circuit Coefficients (at V=Voc, I=0)
    v_int_oc = voc
    m_rec_oc = d2mutau / (v_bi - v_int_oc) if (v_bi - v_int_oc) != 0.0 else 0.0
    if modified_ideality_factor != 0.0:
        m_d_oc = math.exp(v_int_oc / modified_ideality_factor) - 1.0
    else:
        m_d_oc = 0.0
    l_oc = voc / rsh if rsh != 0.0 else 0.0

    # Step 4: Solve the Linear System (solve for Io)
    if m_d_oc != 0.0:
        io = (iph * (1.0 - m_rec_oc) - l_oc) / m_d_oc
    else:
        io = 0.0

    pv_module_data["photocurrent"] = iph
    pv_module_data["diode_saturation_current"] = io

    pv_module_data["modified_ideality_factor"] = modified_ideality_factor

    return pv_module_data
