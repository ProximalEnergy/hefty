import polars as pl
from p01_get_data.source_proximal.s05_qa_met_data import qa_met_data


class TestQCMetData:
    """Test the qc_met_data function, particularly POA zero-to-NaN conversion."""

    def test_poa_zero_to_nan_conversion_with_nonzero_values(self):
        """Test that 0 POA values are converted to NaN when non-zero values exist."""
        # Create proper input format for qc_met_data
        input_data = (
            pl.DataFrame(
                {
                    "time": [
                        "2024-01-01 06:00:00",
                        "2024-01-01 12:00:00",
                        "2024-01-01 18:00:00",
                    ],
                    "met_name": ["device1", "device1", "device1"],
                    "sensor_name": [
                        "met_station_poa",
                        "met_station_poa",
                        "met_station_poa",
                    ],
                    "value_continuous": [0, 800, 0],  # Zero, non-zero, zero
                }
            )
            .vstack(
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 06:00:00",
                            "2024-01-01 12:00:00",
                            "2024-01-01 18:00:00",
                        ],
                        "met_name": ["device1", "device1", "device1"],
                        "sensor_name": [
                            "met_station_ghi",
                            "met_station_ghi",
                            "met_station_ghi",
                        ],
                        "value_continuous": [0, 500, 0],
                    }
                )
            )
            .vstack(
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 06:00:00",
                            "2024-01-01 12:00:00",
                            "2024-01-01 18:00:00",
                        ],
                        "met_name": ["device1", "device1", "device1"],
                        "sensor_name": [
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                        ],
                        "value_continuous": [25, 30, 20],
                    }
                )
            )
        )

        result = qa_met_data(met_data_raw=input_data, use_poa_only=False)

        # Check that 0 POA values were converted to None (NaN)
        poa_values = result.select("poa").to_series()
        assert poa_values[0] is None  # First value was 0, should be None
        assert poa_values[1] == 800  # Second value was non-zero, should remain
        assert poa_values[2] is None  # Third value was 0, should be None

    def test_poa_zero_to_nan_no_conversion_when_all_zeros(self):
        """Test that 0 POA values are NOT converted to NaN when all values are zero."""
        # Create test data with all zero POA values (nighttime scenario)
        input_data = (
            pl.DataFrame(
                {
                    "time": [
                        "2024-01-01 00:00:00",
                        "2024-01-01 01:00:00",
                        "2024-01-01 02:00:00",
                    ],
                    "met_name": ["device1", "device1", "device1"],
                    "sensor_name": [
                        "met_station_poa",
                        "met_station_poa",
                        "met_station_poa",
                    ],
                    "value_continuous": [0, 0, 0],  # All zeros
                }
            )
            .vstack(
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 00:00:00",
                            "2024-01-01 01:00:00",
                            "2024-01-01 02:00:00",
                        ],
                        "met_name": ["device1", "device1", "device1"],
                        "sensor_name": [
                            "met_station_ghi",
                            "met_station_ghi",
                            "met_station_ghi",
                        ],
                        "value_continuous": [0, 0, 0],
                    }
                )
            )
            .vstack(
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 00:00:00",
                            "2024-01-01 01:00:00",
                            "2024-01-01 02:00:00",
                        ],
                        "met_name": ["device1", "device1", "device1"],
                        "sensor_name": [
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                        ],
                        "value_continuous": [5, 4, 3],
                    }
                )
            )
        )

        result = qa_met_data(met_data_raw=input_data, use_poa_only=False)

        # Check that 0 POA values were NOT converted to None (preserved as 0)
        poa_values = result.select("poa").to_series()
        assert poa_values[0] == 0  # Should remain 0
        assert poa_values[1] == 0  # Should remain 0
        assert poa_values[2] == 0  # Should remain 0

    def test_poa_zero_to_nan_no_poa_column(self):
        """Test that function works normally when no POA column exists."""
        # Create test data without POA column
        input_data = pl.DataFrame(
            {
                "time": ["2024-01-01 12:00:00", "2024-01-01 13:00:00"],
                "met_name": ["device1", "device1"],
                "sensor_name": ["met_station_ghi", "met_station_ghi"],
                "value_continuous": [500, 600],
            }
        ).vstack(
            pl.DataFrame(
                {
                    "time": ["2024-01-01 12:00:00", "2024-01-01 13:00:00"],
                    "met_name": ["device1", "device1"],
                    "sensor_name": [
                        "met_station_ambient_temperature",
                        "met_station_ambient_temperature",
                    ],
                    "value_continuous": [25, 30],
                }
            )
        )

        result = qa_met_data(met_data_raw=input_data, use_poa_only=False)

        # Should not have POA column and should not crash
        assert "poa" not in result.columns

    def test_poa_zero_to_nan_with_use_poa_only_true(self):
        """Test POA zero-to-NaN conversion when use_poa_only=True."""
        input_data = pl.DataFrame(
            {
                "time": [
                    "2024-01-01 06:00:00",
                    "2024-01-01 12:00:00",
                    "2024-01-01 18:00:00",
                ],
                "met_name": ["device1", "device1", "device1"],
                "sensor_name": [
                    "met_station_poa",
                    "met_station_poa",
                    "met_station_poa",
                ],
                "value_continuous": [0, 850, 0],  # Zero, non-zero, zero
            }
        ).vstack(
            pl.DataFrame(
                {
                    "time": [
                        "2024-01-01 06:00:00",
                        "2024-01-01 12:00:00",
                        "2024-01-01 18:00:00",
                    ],
                    "met_name": ["device1", "device1", "device1"],
                    "sensor_name": [
                        "met_station_ambient_temperature",
                        "met_station_ambient_temperature",
                        "met_station_ambient_temperature",
                    ],
                    "value_continuous": [20, 25, 22],
                }
            )
        )

        result = qa_met_data(met_data_raw=input_data, use_poa_only=True)

        # Check that 0 POA values were converted to None (NaN)
        poa_values = result.select("poa").to_series()
        assert poa_values[0] is None  # First value was 0, should be None
        assert poa_values[1] == 850  # Second value was non-zero, should remain
        assert poa_values[2] is None  # Third value was 0, should be None

    def test_use_median_irr_sensor_aggregation(self):
        """Test median-based POA aggregation when `use_median_irr_sensor=True`."""
        input_data = pl.concat(
            [
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device1", "device1"],
                        "sensor_name": ["met_station_poa", "met_station_poa"],
                        "value_continuous": [100, 300],  # device1 POA values
                    }
                ),
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device2", "device2"],
                        "sensor_name": ["met_station_poa", "met_station_poa"],
                        "value_continuous": [200, 400],  # device2 POA values
                    }
                ),
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device3", "device3"],
                        "sensor_name": ["met_station_poa", "met_station_poa"],
                        "value_continuous": [
                            800,
                            500,
                        ],  # device3 POA values (high outlier)
                    }
                ),
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device1", "device1"],
                        "sensor_name": [
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                        ],
                        "value_continuous": [25, 30],
                    }
                ),
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device2", "device2"],
                        "sensor_name": [
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                        ],
                        "value_continuous": [26, 31],
                    }
                ),
                pl.DataFrame(
                    {
                        "time": [
                            "2024-01-01 12:00:00",
                            "2024-01-01 13:00:00",
                        ],
                        "met_name": ["device3", "device3"],
                        "sensor_name": [
                            "met_station_ambient_temperature",
                            "met_station_ambient_temperature",
                        ],
                        "value_continuous": [27, 32],
                    }
                ),
            ]
        )

        _result = qa_met_data(met_data_raw=input_data, use_poa_only=True)

        # Test removed - median aggregation moved to s07_combine_met_and_soiling
