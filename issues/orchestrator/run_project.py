"""Single-project orchestration for automated issue detection."""

import datetime
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from core.dependencies import get_project_name_short
from core.enumerations import DeviceType, SensorType
from issues.config.issue_detectors import (
    IssueDetectorConfig,
    get_default_issue_detector_config,
)
from issues.detectors.base import IssueDetector
from issues.detectors.met_station_non_communicating import (
    MetStationNonCommunicatingDetector,
)
from issues.models.detector_context import DetectorContext
from issues.models.issue_candidate import IssueCandidate
from issues.orchestrator.context_builder import build_detector_context
from issues.persistence.repository import IssueRepository
from issues.persistence.run_repository import build_issue_repository
from issues.rectification.engine import IssueRectificationEngine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProjectIssueRunSummary:
    """Run metrics for one project issues orchestration cycle."""

    project_id: str
    run_time: datetime.datetime
    raw_candidate_count: int
    final_candidate_count: int
    opened_count: int
    matched_count: int
    resolved_count: int
    active_count: int


@dataclass(frozen=True)
class DetectorDataRequirements:
    """Unionable data requirements for a detector."""

    device_type_ids: tuple[int, ...]
    sensor_type_ids: tuple[int, ...]
    telemetry_window_minutes: int
    expected_interval_minutes_default: int


@dataclass(frozen=True)
class ConfiguredIssueDetector:
    """Detector instance paired with its required read inputs."""

    detector: IssueDetector
    requirements: DetectorDataRequirements


def run_project_issues(
    *,
    project_id: str,
    run_time: datetime.datetime | None = None,
    config: IssueDetectorConfig | None = None,
) -> ProjectIssueRunSummary:
    """Run issue detectors, rectify candidates, and persist lifecycle changes."""
    detector_config = config or get_default_issue_detector_config()
    now = run_time or datetime.datetime.now(datetime.UTC)
    logger.info("\tStarting issues project run for project_id=%s", project_id)
    project_name_short = _resolve_project_name_short(project_id=project_id)
    repository = build_issue_repository(
        project_name_short=project_name_short,
    )
    logger.info("\tResolved project schema: %s", project_name_short)
    configured_detectors = _build_configured_detectors(
        detector_config=detector_config,
        repository=repository,
    )
    merged_requirements = _merge_detector_requirements(
        requirements=[item.requirements for item in configured_detectors]
    )

    context = build_detector_context(
        project_id=project_id,
        project_name_short=project_name_short,
        run_time=now,
        device_type_ids=merged_requirements.device_type_ids,
        sensor_type_ids=merged_requirements.sensor_type_ids,
        telemetry_window_minutes=merged_requirements.telemetry_window_minutes,
        expected_interval_minutes_default=(
            merged_requirements.expected_interval_minutes_default
        ),
    )

    raw_candidates = _run_detectors(
        detectors=configured_detectors,
        context=context,
    )
    logger.info("\t\tDetector output raw_candidates=%d", len(raw_candidates))
    rectifier = IssueRectificationEngine()
    final_candidates = rectifier.rectify(candidates=raw_candidates)
    logger.info("\t\tRectified candidates=%d", len(final_candidates))
    persistence_result = repository.apply_candidates(
        project_id=project_id,
        run_time=now,
        candidates=final_candidates,
    )
    logger.info(
        "\t\tPersistence result opened=%d matched=%d resolved=%d active=%d",
        persistence_result.opened_count,
        persistence_result.matched_count,
        persistence_result.resolved_count,
        persistence_result.active_count,
    )

    return ProjectIssueRunSummary(
        project_id=project_id,
        run_time=now,
        raw_candidate_count=len(raw_candidates),
        final_candidate_count=len(final_candidates),
        opened_count=persistence_result.opened_count,
        matched_count=persistence_result.matched_count,
        resolved_count=persistence_result.resolved_count,
        active_count=persistence_result.active_count,
    )


def _resolve_project_name_short(*, project_id: str) -> str:
    """Resolve a project schema name from project id or passthrough name_short."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        return project_id
    name_short = get_project_name_short(project_id=project_uuid)
    if name_short is None:
        msg = f"\tCould not resolve project_name_short for project_id={project_id}"
        raise ValueError(msg)
    return name_short


def _build_configured_detectors(
    *,
    detector_config: IssueDetectorConfig,
    repository: IssueRepository,
) -> list[ConfiguredIssueDetector]:
    """Build hard-coded detector registry for a project run."""
    logger.info("\t\tBuilding configured detectors")
    return [
        _build_met_station_non_communicating_detector(
            detector_config=detector_config,
            repository=repository,
        )
    ]


def _build_met_station_non_communicating_detector(
    *,
    detector_config: IssueDetectorConfig,
    repository: IssueRepository,
) -> ConfiguredIssueDetector:
    """Build met station non-communicating detector configuration."""
    met_config = detector_config.met_station_non_communicating
    category_id = repository.get_issue_category_id(
        category_name=met_config.issue_category_name,
    )
    detector = MetStationNonCommunicatingDetector(
        issue_category_id=category_id,
        config=met_config,
    )
    met_sensor_type_ids = tuple(
        SensorType.extract_values(
            enum_list=[
                SensorType.MET_STATION_POA,
                SensorType.MET_STATION_POA_TILT,
                SensorType.MET_STATION_GHI,
                SensorType.MET_STATION_AMBIENT_TEMPERATURE,
                SensorType.MET_STATION_WIND_SPEED,
                SensorType.MET_STATION_RELATIVE_HUMIDITY,
                SensorType.MET_STATION_BOM_TEMPERATURE,
            ]
        )
    )
    requirements = DetectorDataRequirements(
        device_type_ids=(DeviceType.MET_STATION.value,),
        sensor_type_ids=met_sensor_type_ids,
        telemetry_window_minutes=met_config.evaluation_window_minutes,
        expected_interval_minutes_default=met_config.expected_interval_minutes_default,
    )
    logger.info(
        "\t\tConfigured detector met_station_non_communicating category_id=%d",
        category_id,
    )
    return ConfiguredIssueDetector(
        detector=detector,
        requirements=requirements,
    )


def _merge_detector_requirements(
    *,
    requirements: Sequence[DetectorDataRequirements],
) -> DetectorDataRequirements:
    """Merge detector requirements so context data is loaded once."""
    if not requirements:
        msg = "At least one detector must be configured"
        raise ValueError(msg)

    device_type_ids = {
        type_id
        for requirement in requirements
        for type_id in requirement.device_type_ids
    }
    sensor_type_ids = {
        type_id
        for requirement in requirements
        for type_id in requirement.sensor_type_ids
    }
    telemetry_window_minutes = max(
        requirement.telemetry_window_minutes for requirement in requirements
    )
    expected_interval_minutes_default = min(
        requirement.expected_interval_minutes_default for requirement in requirements
    )
    merged = DetectorDataRequirements(
        device_type_ids=tuple(sorted(device_type_ids)),
        sensor_type_ids=tuple(sorted(sensor_type_ids)),
        telemetry_window_minutes=telemetry_window_minutes,
        expected_interval_minutes_default=expected_interval_minutes_default,
    )
    logger.info(
        "\t\tMerged detector requirements device_types=%d sensor_types=%d window=%d",
        len(merged.device_type_ids),
        len(merged.sensor_type_ids),
        merged.telemetry_window_minutes,
    )
    return merged


def _run_detectors(
    *,
    detectors: Sequence[ConfiguredIssueDetector],
    context: DetectorContext,
) -> list[IssueCandidate]:
    """Run each detector over shared context and combine candidates."""
    raw_candidates: list[IssueCandidate] = []
    for configured in detectors:
        candidates = configured.detector.detect(context=context)
        logger.info(
            "\t\tDetector %s produced %d candidates",
            configured.detector.__class__.__name__,
            len(candidates),
        )
        raw_candidates.extend(candidates)
    return raw_candidates
