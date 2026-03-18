import pandas as pd
from app.v1.protected.web_application.projects.device_details.device_details import (
    _get_sorted_horizontal_device_data,
    _get_sorted_vertical_device_data,
)


def test_get_sorted_horizontal_device_data_keeps_natural_device_order():
    """Test that device rows are ordered naturally by numeric device suffix."""
    df = pd.DataFrame(
        {
            10: [10.0, 10.5],
            2: [2.0, 2.5],
            1: [1.0, 1.5],
        }
    )

    result = _get_sorted_horizontal_device_data(
        df=df,
        category="pcs",
        tag_id_to_category={10: "pcs", 2: "pcs", 1: "pcs"},
        tag_id_to_device_name_long={
            10: "PCS 10",
            2: "PCS 2",
            1: "PCS 1",
        },
        tag_id_to_device_id={10: 10, 2: 2, 1: 1},
    )

    assert result == [
        {"values": [1.0, 1.5], "name": "PCS 1", "device_id": 1},
        {"values": [2.0, 2.5], "name": "PCS 2", "device_id": 2},
        {"values": [10.0, 10.5], "name": "PCS 10", "device_id": 10},
    ]


def test_get_sorted_vertical_device_data_keeps_natural_device_order():
    """Test that vertical device rows are ordered naturally by device name."""
    df = pd.DataFrame(
        {
            10: [10.0, 10.5],
            2: [2.0, 2.5],
            1: [1.0, 1.5],
        }
    )

    result = _get_sorted_vertical_device_data(
        df=df,
        tag_id_to_device_name_long={
            10: "PCS 10",
            2: "PCS 2",
            1: "PCS 1",
        },
        tag_id_to_device_id={10: 10, 2: 2, 1: 1},
    )

    assert result == [
        {"values": [1.0, 1.5], "name": "PCS 1", "device_id": 1},
        {"values": [2.0, 2.5], "name": "PCS 2", "device_id": 2},
        {"values": [10.0, 10.5], "name": "PCS 10", "device_id": 10},
    ]
