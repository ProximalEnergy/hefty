"""Tests for project status interpretation helpers."""

import pandas as pd
from core.crud.project.statuses import (
    _detect_binary_alerts,
    _interpret_binary_statuses,
)


def test_binary_status_detects_alert_when_false_deviates_from_nominal_true():
    """A nominal true bit should alert when the reported bit is false."""
    binary_df = pd.DataFrame(
        {
            "lookup_id": [10],
            "value": [0],
        }
    )
    status_binary_df = pd.DataFrame(
        {
            "status_binary_id": [10],
            "bit_position": [0],
            "description": ["Contactor closed"],
            "state_true": ["Closed"],
            "state_false": ["Open"],
            "nominal_state": [True],
            "failure_mode_id": [123],
        }
    )

    alert_mask = _detect_binary_alerts(
        binary_df=binary_df,
        status_binary_df=status_binary_df,
    )
    interpreted_df = _interpret_binary_statuses(
        binary_df=binary_df,
        status_binary_df=status_binary_df,
    )

    assert alert_mask.tolist() == [True]
    assert interpreted_df["alert"].tolist() == [True]
    assert interpreted_df["status"].tolist() == [["Contactor closed: Open"]]
