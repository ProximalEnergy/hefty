import math

import pytest
from app.domain.equipment._utils.enumerations import PANformat
from app.domain.equipment.pv_module.parse_pan.s02_column_mapping import (
    format_pan_to_pvmodule,
)


def _build_text_pan_data(*, technology: str = "Mono-c-Si") -> dict[str, object]:
    return {
        "PVObject_": {
            "Manufacturer": "Jinko",
            "Model": "JKM580N",
            "Technol": technology,
            "PNom": 580.0,
            "Isc": 13.79,
            "Voc": 52.1,
            "Imp": 13.1,
            "Vmp": 44.3,
            "NCelS": 72,
            "NCelP": 1,
            "RSerie": 0.21,
            "RShunt": 450.0,
            "muISC": 0.005,
            "muPmpReq": -0.35,
            "Width": 1.134,
            "Height": 2.278,
            "PVObject_Commercial": {},
        }
    }


def test_format_pan_to_pvmodule_preserves_present_special_values():
    """Keep explicit special PAN values instead of falling back."""
    pan_data = _build_text_pan_data(technology="CdTe")
    pan_data["PVObject_"].update(
        {
            "RShunt0": 275.0,
            "RShuntExp": 6.2,
            "Gamma": 1.34,
            "muGamma": 0.012,
            "muVocSpec": -0.14,
            "D2MuTau": 2.5e-8,
        }
    )
    pan_data["PVObject_"]["PVObject_Commercial"] = {
        "BifacialityFactor": 0.7,
    }

    result = format_pan_to_pvmodule(
        pan_data=pan_data,
        pan_format=PANformat.TEXT,
    )

    assert result["manufacturer"] == "Jinko"
    assert result["beta_voc"] == -0.14
    assert result["bifaciality_factor"] == 0.7
    assert result["r_shunt_0"] == 275.0
    assert result["r_shunt_exponent"] == 6.2
    assert result["diode_ideality_factor"] == 1.34
    assert result["diode_ideality_factor_temp_coefficient"] == 0.012
    assert result["d2mutau"] == 2.5e-8


def test_format_pan_to_pvmodule_applies_expected_fallbacks():
    """Use expected defaults when optional PAN values are missing."""
    result = format_pan_to_pvmodule(
        pan_data=_build_text_pan_data(),
        pan_format=PANformat.TEXT,
    )

    assert result["manufacturer"] == "Jinko"
    assert result["bifaciality_factor"] == 0.0
    assert result["beta_voc"] == pytest.approx(-0.0029 * 52.1)
    assert result["r_shunt_0"] == 450.0
    assert result["r_shunt_exponent"] == 5.5
    assert result["diode_ideality_factor"] == 1.2
    assert result["diode_ideality_factor_temp_coefficient"] == 0.0
    assert math.isnan(result["d2mutau"])
