"""Tests for capacity-field requirement checks."""

import unittest

from core.enumerations import DeviceType

from inspectui.core.capacity_check import check_capacity_requirements
from inspectui.core.models import DeviceInfo


class TestCapacityCheck(unittest.TestCase):
    """Unit tests for capacity check logic."""

    def test_checks_true_requirements_only(self) -> None:
        """TRUE matrix cells create requirements; FALSE/blank cells do not."""
        devices = [
            DeviceInfo(
                device_id=1,
                device_type_id=DeviceType.PV_INVERTER.value,
                name_short="inv-1",  # noqa: hardcoded-name-short
                name_long=None,
                parent_device_id=None,
                capacity_dc=10,
                capacity_ac=None,
            ),
            DeviceInfo(
                device_id=2,
                device_type_id=DeviceType.BESS_STRING.value,
                name_short="string-1",  # noqa: hardcoded-name-short
                name_long=None,
                parent_device_id=None,
                capacity_dc=0,
                capacity_ac=None,
                capacity_energy_dc=None,
            ),
        ]

        rows = check_capacity_requirements(devices=devices)
        by_key = {
            (row.requirement.device_type, row.requirement.field_name): row
            for row in rows
        }

        inverter_ac = by_key[(DeviceType.PV_INVERTER, "capacity_ac")]
        self.assertFalse(inverter_ac.passed)
        self.assertEqual(inverter_ac.missing_devices[0].device_id, 1)

        bess_string_dc = by_key[(DeviceType.BESS_STRING, "capacity_dc")]
        self.assertTrue(bess_string_dc.passed)

        bess_string_energy = by_key[
            (DeviceType.BESS_STRING, "capacity_energy_dc")
        ]
        self.assertFalse(bess_string_energy.passed)
        self.assertEqual(bess_string_energy.missing_devices[0].device_id, 2)

        self.assertNotIn((DeviceType.BESS_STRING, "capacity_ac"), by_key)
        self.assertNotIn((DeviceType.METER, "capacity_dc"), by_key)


if __name__ == "__main__":
    unittest.main()
