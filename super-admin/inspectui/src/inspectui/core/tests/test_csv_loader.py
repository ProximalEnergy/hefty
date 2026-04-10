"""Tests for CSV device/tag loading."""

import tempfile
import unittest
from pathlib import Path

from inspectui.core.csv_loader import (
    load_devices_csv,
    load_tags_csv,
    project_devices_csv_path,
)


class TestCsvLoader(unittest.TestCase):
    """Unit tests for csv_loader."""

    def test_project_devices_csv_path(self) -> None:
        """Devices CSV path uses {root}/{name_short} - devices.csv."""
        p = project_devices_csv_path(root=Path("/data"), name_short="bexar")  # noqa: hardcoded-name-short
        self.assertEqual(p, Path("/data/bexar - devices.csv"))

    def test_load_devices_minimal(self) -> None:
        """Valid devices.csv parses to DeviceInfo rows."""
        content = (
            "device_id,device_type_id,name_short,name_long,"
            "parent_device_id,capacity_dc,capacity_ac\n"
            "10,2,a,b,,1.5,\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "devices.csv"
            p.write_text(content, encoding="utf-8")
            rows = load_devices_csv(path=p)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device_id, 10)
        self.assertEqual(rows[0].device_type_id, 2)
        self.assertEqual(rows[0].name_short, "a")
        self.assertEqual(rows[0].name_long, "b")
        self.assertIsNone(rows[0].parent_device_id)
        self.assertEqual(rows[0].capacity_dc, 1.5)
        self.assertIsNone(rows[0].capacity_ac)
        self.assertIsNone(rows[0].device_model_id)

    def test_load_tags_minimal(self) -> None:
        """Valid tags.csv parses to TagInfo rows."""
        content = (
            "tag_id,device_id,sensor_type_id,data_type_id,name_short,"
            "name_long,name_scada,in_tsdb\n"
            "5,10,,,x,,SCADA.T1,false\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tags.csv"
            p.write_text(content, encoding="utf-8")
            rows = load_tags_csv(path=p)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].tag_id, 5)
        self.assertEqual(rows[0].device_id, 10)
        self.assertFalse(rows[0].in_tsdb)

    def test_missing_column_raises(self) -> None:
        """Omitting a required header raises ValueError."""
        content = "device_id,device_type_id\n1,2\n"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "devices.csv"
            p.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_devices_csv(path=p)
        self.assertIn("missing columns", str(ctx.exception))

    def test_device_model_id_optional_column(self) -> None:
        """Optional device_model_id column is parsed when present."""
        content = (
            "device_id,device_type_id,name_short,name_long,parent_device_id,"
            "capacity_dc,capacity_ac,device_model_id\n"
            "10,2,a,b,,1.5,,42\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "devices.csv"
            p.write_text(content, encoding="utf-8")
            rows = load_devices_csv(path=p)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device_model_id, 42)

    def test_extra_columns_ignored(self) -> None:
        """Extra columns (e.g. from Google Sheets) are ignored."""
        content = (
            "device_id,device_type_id,name_short,name_long,parent_device_id,"
            "capacity_dc,capacity_ac,_device_type,_parent_device,capacity_energy\n"
            "1,2,,,,,,x,y,99\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "devices.csv"
            p.write_text(content, encoding="utf-8")
            rows = load_devices_csv(path=p)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].device_id, 1)

    def test_bad_in_tsdb_raises(self) -> None:
        """Invalid in_tsdb cell raises ValueError."""
        content = (
            "tag_id,device_id,sensor_type_id,data_type_id,name_short,"
            "name_long,name_scada,in_tsdb\n"
            "1,1,,,,,t,maybe\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tags.csv"
            p.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_tags_csv(path=p)
        self.assertIn("in_tsdb", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
