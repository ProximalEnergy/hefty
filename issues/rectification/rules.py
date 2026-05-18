"""Rectification rules for candidate suppression and deduping."""

from issues.models.issue_candidate import IssueCandidate, IssueIdentity

MET_STATION_NON_COMMUNICATING_DETECTOR = "met_station_non_communicating"
POA_SENSOR_OUT_OF_POSITION_DETECTOR = "poa_sensor_out_of_position"


def deduplicate_candidates(
    *,
    candidates: list[IssueCandidate],
) -> list[IssueCandidate]:
    """Keep one candidate per identity with earliest start time."""
    by_identity: dict[IssueIdentity, IssueCandidate] = {}
    for candidate in candidates:
        existing = by_identity.get(candidate.identity)
        if existing is None or candidate.time_start < existing.time_start:
            by_identity[candidate.identity] = candidate
    return list(by_identity.values())


def suppress_poa_position_when_met_station_non_communicating(
    *,
    candidates: list[IssueCandidate],
) -> list[IssueCandidate]:
    """Drop POA position candidates covered by communication candidates."""
    non_communicating_channels = {
        (candidate.identity.device_id, candidate.identity.tag_id)
        for candidate in candidates
        if candidate.detector_name == MET_STATION_NON_COMMUNICATING_DETECTOR
    }
    if not non_communicating_channels:
        return candidates
    return [
        candidate
        for candidate in candidates
        if (
            candidate.detector_name != POA_SENSOR_OUT_OF_POSITION_DETECTOR
            or (candidate.identity.device_id, candidate.identity.tag_id)
            not in non_communicating_channels
        )
    ]
