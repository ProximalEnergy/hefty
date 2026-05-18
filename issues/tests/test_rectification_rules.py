import datetime

from issues.models.issue_candidate import IssueCandidate, IssueIdentity
from issues.rectification.engine import IssueRectificationEngine


def _build_rectification_candidate(
    *,
    detector_name: str,
    issue_category_id: int,
) -> IssueCandidate:
    return IssueCandidate(
        project_id="project-a",
        detector_name=detector_name,
        identity=IssueIdentity(
            device_id=10,
            tag_id=20,
            issue_category_id=issue_category_id,
        ),
        time_start=datetime.datetime(2026, 1, 2, 6, 0, tzinfo=datetime.UTC),
        detector_metadata={"detector_name": detector_name},
    )


def test_non_communicating_candidate_suppresses_poa_position_candidate() -> None:
    """Met station communication candidates supersede POA position candidates."""
    rectifier = IssueRectificationEngine()
    non_communicating = _build_rectification_candidate(
        detector_name="met_station_non_communicating",
        issue_category_id=30,
    )
    poa_position = _build_rectification_candidate(
        detector_name="poa_sensor_out_of_position",
        issue_category_id=31,
    )

    candidates = rectifier.rectify(candidates=[poa_position, non_communicating])

    assert candidates == [non_communicating]
