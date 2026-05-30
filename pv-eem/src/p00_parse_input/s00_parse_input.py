import json
import logging
from dataclasses import dataclass
from typing import Any

from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode


@dataclass(slots=True)
class ParsedInputs:
    """ParsedInputs."""

    kwargs: dict[str, Any]
    project_name_short: str
    simulation_temporal_mode: SimulationTemporalMode
    simulation_start: str | None = None
    simulation_end: str | None = None

    @classmethod
    def parse_inputs(
        cls,
        event: dict[str, Any],
    ):
        # --- Parse ---
        """Run parse_inputs."""
        body = {}
        if "body" in event:
            body = event["body"]

        # Combine query parameters and body
        params: dict = {**event.get("queryStringParameters", {}), **body}
        logging.info(f"Params: {json.dumps(params)}")

        # Extract required parameters
        project_name_short: str | None = params.get("project_name_short")
        simulation_start: str | None = params.get("simulation_start")
        simulation_end: str | None = params.get("simulation_end")
        simulation_temporal_mode: str | None = params.get("simulation_temporal_mode")

        # --- QUALITY CONTROL ---
        # quality control on required parameters
        if not project_name_short:
            raise ValueError(
                {
                    "statusCode": 400,
                    "body": json.dumps(
                        {"error": ("Required parameters:project_name_short")}
                    ),
                }
            )

        if not simulation_temporal_mode:
            raise ValueError(
                {
                    "statusCode": 400,
                    "body": json.dumps(
                        {"error": ("Required parameters:simulation_temporal_mode")}
                    ),
                }
            )

        # Convert simulation_temporal_mode to enum
        try:
            simulation_temporal_mode_enum = SimulationTemporalMode(
                simulation_temporal_mode
            )
        except Exception:
            valid_modes = ", ".join([mode.value for mode in SimulationTemporalMode])
            raise ValueError(
                {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "error": (
                                f"Invalid simulation_temporal_mode: "
                                f"{simulation_temporal_mode}. "
                                f"Must be one of: {valid_modes}"
                            )
                        }
                    ),
                }
            )

        # Remove known parameters and pass the rest as kwargs
        known_params = {
            "project_name_short",
            "simulation_temporal_mode",
            "simulation_start",
            "simulation_end",
        }
        kwargs = {k: v for k, v in params.items() if k not in known_params}

        # logging
        logging.info(f"start: {simulation_start}")
        logging.info(f"end: {simulation_end}")

        return cls(
            project_name_short=project_name_short,
            simulation_temporal_mode=simulation_temporal_mode_enum,
            simulation_start=simulation_start,
            simulation_end=simulation_end,
            kwargs=kwargs,
        )
