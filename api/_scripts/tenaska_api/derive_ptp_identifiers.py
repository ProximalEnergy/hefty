"""Derive PTP identifiers from a qse_project_identifier (Entity ID) via the PTP API.

Given a qse_project_identifier (e.g. from operational.qse_integrations),
discovers and prints the corresponding:
- Entity ID (input)
- Generator ID (from Generator-Performance / Real-Time-Unit-Position)
- Resource ID (string, from MktInput-5Min Resource_ID datapoint)
- Settlement Point ID (for Market-Prices endpoint)
- COP ID (Generator Configuration, for COP endpoints)

Run from the api directory (so app and TPS token are available):

  cd api && uv run python _scripts/tenaska_api/derive_ptp_identifiers.py \\
    23dd0644-1056-4308-ad82-af0a6a12d5ac
  cd api && uv run python _scripts/tenaska_api/derive_ptp_identifiers.py \\
    beb9bf6f-8052-4196-b092-fd5cf2db29b8

Note: COP_ID is the first Generator Configuration found for the entity; there
may be multiple (e.g. BEXAR_ES_ESR1 vs BEXAR_ES_BESS1). Verify against PTP docs
if needed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import get_tps_token_manager


def _time_range(
    *,
    days_back: int = 1,
    hours_forward: int = 2,
) -> tuple[str, str]:
    """Return (begin, end) ISO UTC strings for PTP API queries.

    Args:
        days_back: Days before now for begin.
        hours_forward: Hours after now for end.
    """
    now = datetime.now(UTC)
    begin = (now - timedelta(days=days_back)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=hours_forward)).isoformat().replace("+00:00", "Z")
    return begin, end


def _parent_id(entry: dict) -> str | None:
    """Get parent identifier from entry (API may use camelCase or snake_case).

    Args:
        entry: API response entry dict.
    """
    return entry.get("parentIdentifier") or entry.get("parent_identifier")


async def _get_generator_id(
    *,
    token: str,
    entity_id: str,
) -> str | None:
    """Find Generator ID for this entity (child with definition Generator).

    Args:
        token: PTP API token.
        entity_id: QSE project (entity) identifier.
    """
    begin, end = _time_range()
    for endpoint in ("Generator-Performance", "Real-Time-Unit-Position"):
        data = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[entity_id],
            begin=begin,
            end=end,
        )
        for entry in data.get("data") or []:
            if not isinstance(entry, dict) or entry.get("definition") != "Generator":
                continue
            ident = entry.get("identifier")
            if isinstance(ident, str):
                return ident
    return None


async def _get_resource_id(
    *,
    token: str,
    generator_id: str | None,
    entity_id: str,
) -> str | None:
    """Extract Resource_ID string from MktInput-5Min (e.g. BEXAR_ES_ESR1).

    Args:
        token: PTP API token.
        generator_id: Generator ID if known, else fallback to entity_id.
        entity_id: QSE project (entity) identifier.
    """
    begin, end = _time_range()
    elements = [generator_id] if generator_id else [entity_id]
    data = await ptp_explorer.get_endpoint_data(
        token=token,
        market="ERCOTNodal",
        endpoint="MktInput-5Min",
        elements=elements,
        begin=begin,
        end=end,
    )
    entries = data.get("data") or []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for dp in entry.get("dataPoints") or []:
            if not isinstance(dp, dict) or dp.get("keyName") != "Resource_ID":
                continue
            values = dp.get("values") or []
            if values and isinstance(values[0], dict):
                value_data = values[0].get("data") or []
                if value_data and isinstance(value_data[0], dict):
                    val = value_data[0].get("value")
                    if isinstance(val, str) and val.strip():
                        return val.strip()
    return None


def _settlement_point_name_from_resource(resource_id: str) -> str | None:
    """Heuristic: BEXAR_ES_ESR1 -> BEXAR_ES_RN; CONT_... -> look for CONT.

    Args:
        resource_id: Resource ID string (e.g. from MktInput-5Min).
    """
    if not resource_id or "_" not in resource_id:
        return None
    parts = resource_id.split("_")
    if len(parts) >= 2:
        prefix = f"{parts[0]}_{parts[1]}"
        return prefix
    return None


async def _get_settlement_point_id(
    *,
    token: str,
    resource_id: str | None,
    _entity_id: str,
) -> str | None:
    """Find Settlement Point ID for Market-Prices (e.g. BEXAR_ES_RN).

    Args:
        token: PTP API token.
        resource_id: Resource ID to derive settlement prefix from.
        _entity_id: Unused; kept for API consistency.
    """
    begin, end = _time_range(days_back=0, hours_forward=1)
    data = await ptp_explorer.get_endpoint_data(
        token=token,
        market="ERCOTNodal",
        endpoint="Market-Prices",
        elements=None,
        begin=begin,
        end=end,
    )
    candidates: list[dict[str, str]] = []
    for entry in data.get("data") or []:
        if not isinstance(entry, dict) or entry.get("definition") != "Settlement Point":
            continue
        ident = entry.get("identifier")
        name = (entry.get("element") or "").strip()
        if ident:
            candidates.append({"identifier": ident, "element": name})

    prefix = _settlement_point_name_from_resource(resource_id) if resource_id else None
    if prefix:
        prefix_upper = prefix.upper()
        for c in candidates:
            if prefix_upper in (c.get("element") or "").upper():
                return c.get("identifier")

    for c in candidates[:5]:
        ident = c.get("identifier")
        if not ident:
            continue
        try:
            data = await ptp_explorer.get_endpoint_data(
                token=token,
                market="ERCOTNodal",
                endpoint="Market-Prices",
                elements=[ident],
                begin=begin,
                end=end,
            )
            if data.get("data"):
                return ident
        except Exception:
            continue
    return None


async def _get_cop_id(
    *,
    token: str,
    entity_id: str,
) -> str | None:
    """Find Generator Configuration ID for COP endpoints.

    Args:
        token: PTP API token.
        entity_id: QSE project (entity) identifier.
    """
    begin, end = _time_range(days_back=2)
    data = await ptp_explorer.get_endpoint_data(
        token=token,
        market="ERCOTNodal",
        endpoint="Submissions-Current-Operating-Plan-RTC",
        elements=None,
        begin=begin,
        end=end,
    )
    entries = data.get("data") or []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("definition") == "Generator Configuration":
            parent = entry.get("parentIdentifier")
            if parent == entity_id:
                ident = entry.get("identifier")
                if isinstance(ident, str):
                    return ident
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("definition") == "Generator Configuration":
            ident = entry.get("identifier")
            if isinstance(ident, str):
                return ident
    return None


async def _run_chain(
    *,
    token: str,
    entity_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Generator -> resource_id -> settlement_point_id (sequential)."""
    generator_id = await _get_generator_id(token=token, entity_id=entity_id)
    resource_id = await _get_resource_id(
        token=token,
        generator_id=generator_id,
        entity_id=entity_id,
    )
    settlement_point_id = await _get_settlement_point_id(
        token=token,
        resource_id=resource_id,
        _entity_id=entity_id,
    )
    return generator_id, resource_id, settlement_point_id


async def run_identifier_derivation(entity_id: str) -> dict[str, str | None]:
    """Derive all identifiers for the given qse_project_identifier (Entity ID).

    Args:
        entity_id: QSE project identifier (Entity ID from PTP).
    """
    token_manager = get_tps_token_manager()
    token = await token_manager.get_token()

    (generator_id, resource_id, settlement_point_id), cop_id = await asyncio.gather(
        _run_chain(token=token, entity_id=entity_id),
        _get_cop_id(token=token, entity_id=entity_id),
    )

    return {
        "entity_id": entity_id,
        "generator_id": generator_id,
        "resource_id": resource_id,
        "settlement_point_id": settlement_point_id,
        "cop_id": cop_id,
    }


def derive_ptp_identifiers() -> int:
    """CLI entrypoint: parse args, run derivation, print results."""
    parser = argparse.ArgumentParser(
        description="Derive PTP identifiers from qse_project_identifier (Entity ID)"
    )
    parser.add_argument(
        "qse_project_identifier",
        help="Entity ID (e.g. 23dd0644-1056-4308-ad82-af0a6a12d5ac)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print only provider_config JSON (for qse_integrations)",
    )
    args = parser.parse_args()
    entity_id = args.qse_project_identifier.strip()
    if not entity_id:
        print("Error: qse_project_identifier is required", file=sys.stderr)
        return 1

    result = asyncio.run(run_identifier_derivation(entity_id))

    if args.json:
        provider_config = {
            "cop_id": result["cop_id"] or "",
            "entity_id": result["entity_id"] or "",
            "resource_id": result["resource_id"] or "",
            "generator_id": result["generator_id"] or "",
            "settlement_point_id": result["settlement_point_id"] or "",
        }
        print(json.dumps(provider_config, indent=2))
        return 0

    print("PTP identifiers derived from qse_project_identifier (Entity ID):")
    print()
    print(f"  ENTITY_ID (input)       = {result['entity_id']!r}")
    print(f"  GENERATOR_ID            = {result['generator_id']!r}")
    print(f"  RESOURCE_ID (string)    = {result['resource_id']!r}")
    print(f"  SETTLEMENT_POINT_ID    = {result['settlement_point_id']!r}")
    print(f"  COP_ID                 = {result['cop_id']!r}")
    print()
    print("Python constants (for ptp_data.py / config):")
    print()
    print(f'ENTITY_ID = "{result["entity_id"]}"')
    if result["generator_id"]:
        print(f'GENERATOR_ID = "{result["generator_id"]}"')
    if result["resource_id"]:
        print(f'RESOURCE_ID = "{result["resource_id"]}"')
    if result["settlement_point_id"]:
        print(
            f"# Settlement point for Market-Prices\n"
            f'SETTLEMENT_POINT_ID = "{result["settlement_point_id"]}"'
        )
    if result["cop_id"]:
        print("# Generator Configuration for COP endpoints")
        print(f'COP_ID = "{result["cop_id"]}"')
    return 0


if __name__ == "__main__":
    sys.exit(derive_ptp_identifiers())
