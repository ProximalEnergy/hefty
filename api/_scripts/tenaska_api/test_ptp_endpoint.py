"""Generic test script to determine required parameters for any PTP endpoint.

Usage:
    python test_ptp_endpoint.py <endpoint_name> [options]

Examples:
    # Test COP endpoint with default Bexar settings
    python test_ptp_endpoint.py "Submissions-Current-Operating-Plan"

    # Test Generator Performance endpoint
    python test_ptp_endpoint.py "Generator-Performance"

    # Test with different resource filter
    python test_ptp_endpoint.py "Load-Performance" --resource-filter "MOORE"

    # Skip schema and viewport tests for faster execution
    python test_ptp_endpoint.py "Settlement-DA" --skip-schema --skip-viewport
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import sys
from datetime import UTC, timedelta
from pathlib import Path

# Add the api directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import get_tps_token_manager

# Bexar identifiers (can be overridden)
# Generator-level identifiers
BEXAR_GENERATOR_ID = "53db134c-05a9-4091-a49d-91c65b9e32df"  # Bexar ESS ESR
BEXAR_COP_ID = "01ada09d-853c-47c9-8b49-dff77388e37c"  # BEXAR_ES_ESR1

# Entity-level identifiers
BEXAR_ENTITY_ID = "23dd0644-1056-4308-ad82-af0a6a12d5ac"  # Bexar ESS LLC
BEXAR_ESS_ESR_ENTITY = "52b81dd4-c81b-4c2d-8742-058389691c2a"  # Bexar ESS - ESR
BEXAR_CUSTOMER_OPT = (
    "f01017f3-c682-45e1-a81a-8710d56a6c1e"  # Bexar - Customer Optimization
)
BEXAR_BESS = "c9e0c683-135a-4bbb-8ab3-e80f28ed5a96"  # Bexar BESS
BEXAR_BESS_GEN = "ccfc6de6-43c8-428e-ac91-b03706a22325"  # Bexar BESS - Gen
BEXAR_BESS_CLR = "c67f3121-0f5d-42f1-a465-ff3eb71956b8"  # Bexar BESS - CLR

# All Bexar identifiers to test
ALL_BEXAR_IDENTIFIERS = [
    {
        "id": BEXAR_GENERATOR_ID,
        "name": "Bexar ESS ESR",
        "type": "Generator",
    },
    {
        "id": BEXAR_COP_ID,
        "name": "BEXAR_ES_ESR1",
        "type": "Generator Configuration",
    },
    {
        "id": BEXAR_ENTITY_ID,
        "name": "Bexar ESS LLC",
        "type": "Entity",
    },
    {
        "id": BEXAR_ESS_ESR_ENTITY,
        "name": "Bexar ESS - ESR",
        "type": "Entity",
    },
    {
        "id": BEXAR_CUSTOMER_OPT,
        "name": "Bexar - Customer Optimization",
        "type": "Entity",
    },
    {
        "id": BEXAR_BESS,
        "name": "Bexar BESS",
        "type": "Entity",
    },
    {
        "id": BEXAR_BESS_GEN,
        "name": "Bexar BESS - Gen",
        "type": "Entity",
    },
    {
        "id": BEXAR_BESS_CLR,
        "name": "Bexar BESS - CLR",
        "type": "Entity",
    },
]

BEXAR_RESOURCE_ID = "BEXAR_ES_ESR1"


def has_real_data(
    entry: dict, skip_metadata_fields: list[str] | None = None
) -> tuple[bool, int]:
    """Check if entry has real data (not just metadata fields).

    Args:
        entry: Data entry from PTP API
        skip_metadata_fields: List of field names to skip (default: ["Resource_ID"])

    Returns:
        Tuple of (has_data, interval_count)
    """
    if skip_metadata_fields is None:
        skip_metadata_fields = ["Resource_ID"]

    data_points = entry.get("dataPoints", [])
    interval_count = 0
    has_data = False

    for dp in data_points:
        key_name = dp.get("keyName", "")
        if key_name in skip_metadata_fields:
            continue  # Skip metadata fields

        values = dp.get("values", [])
        for val in values:
            if isinstance(val, dict):
                interval = val.get("intervalStartUtc", "")
                # Filter out placeholder dates
                if interval and "1753" not in interval and "1900" not in interval:
                    try:
                        parsed_date = datetime.datetime.fromisoformat(
                            interval.replace("Z", "+00:00")
                        )
                        # Check if it's a reasonable date
                        if 2015 <= parsed_date.year <= 2030:
                            value_data = val.get("data", [])
                            if value_data and len(value_data) > 0:
                                value = value_data[0].get("value")
                                if value is not None:
                                    has_data = True
                                    interval_count += 1
                                    break
                    except Exception:
                        continue
        if has_data:
            break

    return has_data, interval_count


async def test_without_elements(
    token: str, endpoint: str, resource_filter: str | None = None
) -> dict:
    """Test 1: Query without element filter to see all identifiers.

    Args:
        token: PTP API token
        endpoint: Endpoint name to test
        resource_filter: Optional resource name to filter for (e.g., "BEXAR")
    """
    print("\n" + "=" * 80)
    print("TEST 1: Query without element filter")
    print(f"Endpoint: {endpoint}")
    print("=" * 80)

    now = datetime.datetime.now(UTC)
    begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    try:
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=None,
            begin=begin,
            end=end,
        )

        if "data" in result:
            entries = result["data"]
            print(f"✅ Found {len(entries)} entries")

            bexar_entries = []
            for entry in entries:
                entry_id = entry.get("identifier")
                data_points = entry.get("dataPoints", [])

                # Extract Resource_ID
                resource_id = None
                for dp in data_points:
                    if dp.get("keyName") == "Resource_ID":
                        values = dp.get("values", [])
                        for val in values:
                            if isinstance(val, dict):
                                value_data = val.get("data", [])
                                if value_data and len(value_data) > 0:
                                    resource_id = str(value_data[0].get("value", ""))
                                    break
                        break

                # Check for resource filter
                if resource_filter:
                    if resource_id and resource_filter.upper() in resource_id.upper():
                        has_data, interval_count = has_real_data(entry)
                        bexar_entries.append(
                            {
                                "identifier": entry_id,
                                "resource_id": resource_id,
                                "has_data": has_data,
                                "interval_count": interval_count,
                            }
                        )
                        print(
                            f"  📋 {entry_id} → {resource_id} "
                            f"({'✅ Has data' if has_data else '❌ No data'})"
                        )
                else:
                    # If no filter, show all entries
                    has_data, interval_count = has_real_data(entry)
                    if has_data:
                        bexar_entries.append(
                            {
                                "identifier": entry_id,
                                "resource_id": resource_id or "N/A",
                                "has_data": has_data,
                                "interval_count": interval_count,
                            }
                        )
                        print(
                            f"  📋 {entry_id} → {resource_id or 'N/A'} "
                            f"({'✅ Has data' if has_data else '❌ No data'})"
                        )

            return {
                "success": True,
                "total_entries": len(entries),
                "bexar_entries": bexar_entries,
            }
        else:
            print("❌ No data in response")
            return {"success": False, "reason": "No data in response"}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


async def test_with_element_id(
    token: str, endpoint: str, element_id: str, test_name: str, verbose: bool = True
) -> dict:
    """Test querying with a specific element ID.

    Args:
        token: PTP API token
        endpoint: Endpoint name
        element_id: Element identifier to test
        test_name: Display name for the test
        verbose: Whether to print detailed output (default: True)
    """
    if verbose:
        print(f"\n{'=' * 80}")
        print(f"TEST: {test_name}")
        print(f"Endpoint: {endpoint}")
        print(f"Element ID: {element_id}")
        print("=" * 80)

    now = datetime.datetime.now(UTC)
    begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    try:
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[element_id],
            begin=begin,
            end=end,
        )

        if "data" in result and result["data"]:
            entry = result["data"][0]
            data_points = entry.get("dataPoints", [])

            if verbose:
                print(f"✅ Got response with {len(data_points)} data points")

            # Analyze data points
            cop_fields = []
            resource_id = None

            for dp in data_points:
                key_name = dp.get("keyName", "")
                values = dp.get("values", [])

                if key_name == "Resource_ID":
                    for val in values:
                        if isinstance(val, dict):
                            value_data = val.get("data", [])
                            if value_data and len(value_data) > 0:
                                resource_id = str(value_data[0].get("value", ""))
                                break
                else:
                    # Check for real COP data
                    real_intervals = 0
                    for val in values:
                        if isinstance(val, dict):
                            interval = val.get("intervalStartUtc", "")
                            if (
                                interval
                                and "1753" not in interval
                                and "1900" not in interval
                            ):
                                try:
                                    parsed_date = datetime.datetime.fromisoformat(
                                        interval.replace("Z", "+00:00")
                                    )
                                    if 2015 <= parsed_date.year <= 2030:
                                        value_data = val.get("data", [])
                                        if value_data and len(value_data) > 0:
                                            value = value_data[0].get("value")
                                            if value is not None:
                                                real_intervals += 1
                                except Exception:
                                    continue

                    if real_intervals > 0:
                        cop_fields.append(
                            {
                                "keyName": key_name,
                                "intervals": real_intervals,
                            }
                        )

            if verbose:
                print(f"  Resource_ID: {resource_id or 'N/A'}")
                print(f"  Data Fields with data: {len(cop_fields)}")
                for field in cop_fields[:10]:  # Show first 10
                    print(f"    - {field['keyName']}: {field['intervals']} intervals")
                if len(cop_fields) > 10:
                    print(f"    ... and {len(cop_fields) - 10} more")
            else:
                # Compact output for iterative testing
                total_intervals = sum(field.get("intervals", 0) for field in cop_fields)
                print(
                    f"    ✅ {len(cop_fields)} fields, "
                    f"{total_intervals} total intervals"
                )

            return {
                "success": True,
                "resource_id": resource_id,
                "data_fields": cop_fields,
                "has_data": len(cop_fields) > 0,
            }
        else:
            print("❌ No data in response")
            return {"success": False, "reason": "No data in response"}
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


async def test_operating_day_range(token: str, endpoint: str, element_id: str) -> dict:
    """Test with operating day boundaries (start of day CT to end of day CT)."""
    print(f"\n{'=' * 80}")
    print("TEST: Operating Day Range (CT timezone)")
    print(f"Endpoint: {endpoint}")
    print(f"Element ID: {element_id}")
    print("=" * 80)

    # Get today in CT timezone
    import pytz

    ct_tz = pytz.timezone("America/Chicago")
    now_ct = datetime.datetime.now(ct_tz)
    today_start_ct = now_ct.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_ct = today_start_ct + timedelta(days=1)

    # Convert to UTC
    today_start_utc = today_start_ct.astimezone(UTC)
    today_end_utc = today_end_ct.astimezone(UTC)

    begin = today_start_utc.isoformat().replace("+00:00", "Z")
    end = today_end_utc.isoformat().replace("+00:00", "Z")

    print(f"  Operating Day: {today_start_ct.strftime('%Y-%m-%d')} CT")
    print(f"  Range: {begin} to {end}")

    try:
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[element_id],
            begin=begin,
            end=end,
        )

        if "data" in result and result["data"]:
            entry = result["data"][0]
            has_data, interval_count = has_real_data(entry)

            print("  ✅ Response received")
            print(f"  Has COP data: {has_data}")
            print(f"  Interval count: {interval_count}")

            return {
                "success": True,
                "has_cop_data": has_data,
                "interval_count": interval_count,
            }
        else:
            print("  ❌ No data in response")
            return {"success": False, "reason": "No data in response"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"success": False, "error": str(e)}


async def test_different_date_ranges(
    token: str, endpoint: str, element_id: str
) -> dict:
    """Test with different date ranges."""
    print(f"\n{'=' * 80}")
    print("TEST: Different Date Ranges")
    print(f"Endpoint: {endpoint}")
    print(f"Element ID: {element_id}")
    print("=" * 80)

    now = datetime.datetime.now(UTC)
    test_ranges = [
        ("Last 24 hours", now - timedelta(hours=24), now),
        ("Last 7 days", now - timedelta(days=7), now),
        ("Last 30 days", now - timedelta(days=30), now),
        ("Today (CT)", None, None),  # Will be calculated
        ("Yesterday (CT)", None, None),  # Will be calculated
    ]

    results = []

    for range_name, start, end in test_ranges:
        if start is None or end is None:
            # Calculate CT day boundaries
            import pytz

            ct_tz = pytz.timezone("America/Chicago")
            now_ct = datetime.datetime.now(ct_tz)
            if "Today" in range_name:
                day_start = now_ct.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
            else:  # Yesterday
                day_start = now_ct.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) - timedelta(days=1)
                day_end = day_start + timedelta(days=1)

            start = day_start.astimezone(UTC)
            end = day_end.astimezone(UTC)

        begin = start.isoformat().replace("+00:00", "Z")
        end_str = end.isoformat().replace("+00:00", "Z")

        print(f"\n  Testing: {range_name}")
        print(f"    Range: {begin} to {end_str}")

        try:
            result = await ptp_explorer.get_endpoint_data(
                token=token,
                market="ERCOTNodal",
                endpoint=endpoint,
                elements=[element_id],
                begin=begin,
                end=end_str,
            )

            if "data" in result and result["data"]:
                entry = result["data"][0]
                has_data, interval_count = has_real_data(entry)

                print(f"    ✅ Has COP data: {has_data}, Intervals: {interval_count}")
                results.append(
                    {
                        "range": range_name,
                        "has_data": has_data,
                        "interval_count": interval_count,
                    }
                )
            else:
                print("    ❌ No data")
                results.append({"range": range_name, "has_data": False})
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append({"range": range_name, "error": str(e)})

    return {"success": True, "results": results}


async def test_endpoint_schema(token: str, endpoint: str) -> dict:
    """Test: Get endpoint schema to see available data points."""
    print(f"\n{'=' * 80}")
    print("TEST: Endpoint Schema Analysis")
    print(f"Endpoint: {endpoint}")
    print("=" * 80)

    try:
        schema = await ptp_explorer.get_endpoint_schema(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
        )

        print("✅ Schema retrieved")

        # Display full endpoint information
        print("\n  📋 Endpoint Details:")
        # Show all top-level keys in the schema
        top_level_keys = [k for k in schema.keys() if k != "data" and k != "dataPoints"]
        if top_level_keys:
            for key in top_level_keys:
                value = schema.get(key)
                if isinstance(value, str | int | float | bool | type(None)):
                    print(f"    {key}: {value}")
                elif isinstance(value, dict):
                    print(f"    {key}: {list(value.keys())}")
                elif isinstance(value, list):
                    print(f"    {key}: [{len(value)} items]")
                else:
                    print(f"    {key}: {type(value).__name__}")
        else:
            print("    (No top-level metadata found)")

        # Also check if there's a nested structure
        if "data" in schema and isinstance(schema["data"], dict):
            data_keys = [k for k in schema["data"].keys() if k != "dataPoints"]
            if data_keys:
                print("\n  📋 Data Section Keys:")
                for key in data_keys:
                    value = schema["data"].get(key)
                    if isinstance(value, str | int | float | bool | type(None)):
                        print(f"    {key}: {value}")
                    elif isinstance(value, dict):
                        print(f"    {key}: {list(value.keys())}")
                    elif isinstance(value, list):
                        print(f"    {key}: [{len(value)} items]")
                    else:
                        print(f"    {key}: {type(value).__name__}")

        # Extract data points
        data_points = None
        if "data" in schema:
            if isinstance(schema["data"], dict) and "dataPoints" in schema["data"]:
                data_points = schema["data"]["dataPoints"]
            elif isinstance(schema["data"], list):
                data_points = schema["data"]
        elif "dataPoints" in schema:
            data_points = schema["dataPoints"]

        if data_points:
            print(f"\n  Available Data Points ({len(data_points)}):")
            cop_fields = []
            for dp in data_points:
                if isinstance(dp, dict):
                    key_name = dp.get("keyName") or dp.get("name") or "Unknown"
                    data_type = dp.get("dataType") or dp.get("type") or "Unknown"
                    is_input = dp.get("isInput", False)
                    input_marker = " [INPUT]" if is_input else ""

                    # Skip common metadata fields
                    if key_name not in ["Resource_ID", "identifier", "element"]:
                        cop_fields.append(key_name)

                    print(f"    - {key_name} ({data_type}){input_marker}")

            print(f"\n  Data Fields (excluding metadata): {len(cop_fields)}")
            for field in cop_fields[:20]:  # Show first 20
                print(f"    - {field}")
            if len(cop_fields) > 20:
                print(f"    ... and {len(cop_fields) - 20} more")

            return {
                "success": True,
                "data_points": data_points,
                "cop_fields": cop_fields,
            }
        else:
            print("  ⚠️  No data points found in schema")
            return {"success": False, "reason": "No data points in schema"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def test_with_environment(token: str, endpoint: str, element_id: str) -> dict:
    """Test: Query with environment parameter."""
    print(f"\n{'=' * 80}")
    print("TEST: With Environment Parameter")
    print(f"Endpoint: {endpoint}")
    print(f"Element ID: {element_id}")
    print("=" * 80)

    now = datetime.datetime.now(UTC)
    begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    # Try different environment values
    environments = ["Production", "production", "PROD", "prod", None]

    for env in environments:
        env_str = env or "None"
        print(f"\n  Testing environment: {env_str}")

        try:
            result = await ptp_explorer.get_endpoint_data(
                token=token,
                market="ERCOTNodal",
                endpoint=endpoint,
                elements=[element_id],
                begin=begin,
                end=end,
                environment=env,
            )

            if "data" in result and result["data"]:
                entry = result["data"][0]
                has_data, interval_count = has_real_data(entry)
                print(f"    ✅ Has COP data: {has_data}, Intervals: {interval_count}")

                if has_data:
                    return {
                        "success": True,
                        "environment": env,
                        "interval_count": interval_count,
                    }
            else:
                print("    ❌ No data")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    return {"success": False, "reason": "No environment worked"}


async def test_with_viewport(token: str, endpoint: str) -> dict:
    """Test: Query elements with viewport parameter."""
    print(f"\n{'=' * 80}")
    print("TEST: Elements with Viewport")
    print(f"Endpoint: {endpoint}")
    print("=" * 80)

    # Try different viewport dates
    now = datetime.datetime.now(UTC)
    viewports = [
        now.strftime("%Y-%m-%d"),
        (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        (now - timedelta(days=7)).strftime("%Y-%m-%d"),
    ]

    for viewport in viewports:
        print(f"\n  Testing viewport: {viewport}")

        try:
            elements = await ptp_explorer.get_endpoint_elements(
                token=token,
                market="ERCOTNodal",
                endpoint=endpoint,
                viewport=viewport,
            )

            if "data" in elements:
                element_list = elements["data"]
                print(f"    ✅ Found {len(element_list)} elements")

                # Look for Bexar
                for elem in element_list[:10]:  # Check first 10
                    if isinstance(elem, dict):
                        identifier = elem.get("identifier") or elem.get("id", "")
                        element_name = elem.get("element") or elem.get("name", "")
                        print(f"      - {identifier}: {element_name}")
            else:
                print("    ⚠️  No data in response")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    return {"success": True}


async def test_query_all_identifiers(
    token: str, endpoint: str, resource_filter: str | None = None
) -> dict:
    """Test: Query each identifier individually to find one with data."""
    print(f"\n{'=' * 80}")
    print("TEST: Query All Identifiers Individually")
    print(f"Endpoint: {endpoint}")
    if resource_filter:
        print(f"Resource Filter: {resource_filter}")
    print("=" * 80)

    now = datetime.datetime.now(UTC)
    begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    # First get all identifiers
    try:
        all_data = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=None,
            begin=begin,
            end=end,
        )

        if "data" not in all_data:
            print("  ❌ No data returned")
            return {"success": False}

        entries = all_data["data"]
        print(f"  Found {len(entries)} total entries")

        # Test each identifier
        best_result = None
        best_interval_count = 0

        for i, entry in enumerate(entries):
            entry_id = entry.get("identifier")
            if not entry_id:
                continue

            print(f"\n  [{i + 1}/{len(entries)}] Testing: {entry_id}")

            try:
                result = await ptp_explorer.get_endpoint_data(
                    token=token,
                    market="ERCOTNodal",
                    endpoint=endpoint,
                    elements=[entry_id],
                    begin=begin,
                    end=end,
                )

                if "data" in result and result["data"]:
                    test_entry = result["data"][0]
                    has_data, interval_count = has_real_data(test_entry)

                    # Get Resource_ID
                    resource_id = None
                    for dp in test_entry.get("dataPoints", []):
                        if dp.get("keyName") == "Resource_ID":
                            values = dp.get("values", [])
                            for val in values:
                                if isinstance(val, dict):
                                    value_data = val.get("data", [])
                                    if value_data and len(value_data) > 0:
                                        resource_id = str(
                                            value_data[0].get("value", "")
                                        )
                                        break
                            break

                    print(f"    Resource_ID: {resource_id}")
                    print(f"    Has COP data: {has_data}, Intervals: {interval_count}")

                    if has_data and interval_count > best_interval_count:
                        best_interval_count = interval_count
                        best_result = {
                            "identifier": entry_id,
                            "resource_id": resource_id,
                            "interval_count": interval_count,
                        }
                        print(f"    ✅ NEW BEST! ({interval_count} intervals)")
            except Exception as e:
                print(f"    ❌ Error: {e}")

        if best_result:
            print("\n  🏆 Best result:")
            print(f"    Identifier: {best_result['identifier']}")
            print(f"    Resource_ID: {best_result['resource_id']}")
            print(f"    Intervals: {best_result['interval_count']}")
            return {"success": True, "best": best_result}
        else:
            print("\n  ⚠️  No identifier found with data")
            return {"success": False, "reason": "No COP data found in any identifier"}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def analyze_data_structure(token: str, endpoint: str, element_id: str) -> dict:
    """Analyze the full data structure returned."""
    print(f"\n{'=' * 80}")
    print("TEST: Full Data Structure Analysis")
    print(f"Endpoint: {endpoint}")
    print(f"Element ID: {element_id}")
    print("=" * 80)

    now = datetime.datetime.now(UTC)
    begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

    try:
        result = await ptp_explorer.get_endpoint_data(
            token=token,
            market="ERCOTNodal",
            endpoint=endpoint,
            elements=[element_id],
            begin=begin,
            end=end,
        )

        if "data" in result and result["data"]:
            entry = result["data"][0]
            data_points = entry.get("dataPoints", [])

            print("\n  Entry Structure:")
            print(f"    Identifier: {entry.get('identifier')}")
            print(f"    Element: {entry.get('element')}")
            print(f"    Definition: {entry.get('definition')}")
            print(f"    Data Points: {len(data_points)}")

            print("\n  Data Points Detail:")
            for dp in data_points:
                key_name = dp.get("keyName", "Unknown")
                values = dp.get("values", [])

                print(f"\n    📊 {key_name}:")
                print(f"      Values count: {len(values)}")

                if values:
                    # Analyze first few values
                    for i, val in enumerate(values[:3]):
                        if isinstance(val, dict):
                            interval_start = val.get("intervalStartUtc", "N/A")
                            interval_end = val.get("intervalEndUtc", "N/A")
                            value_data = val.get("data", [])

                            print(f"      Value [{i + 1}]:")
                            print(
                                f"        Interval: {interval_start} to {interval_end}"
                            )
                            print(f"        Data: {value_data}")

                            if value_data and len(value_data) > 0:
                                print(f"        data[0]: {value_data[0]}")
                                if isinstance(value_data[0], dict):
                                    print(
                                        "        data[0] keys:",
                                        list(value_data[0].keys()),
                                    )
                                    for k, v in value_data[0].items():
                                        type_name = type(v).__name__
                                        print(f"          {k}: {v} (type: {type_name})")

            return {"success": True, "structure": entry}
        else:
            print("  ❌ No data in response")
            return {"success": False}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def run_test_ptp_endpoint_cli():
    """Run the PTP endpoint test CLI."""
    parser = argparse.ArgumentParser(
        description="Test PTP endpoint parameters to determine required inputs"
    )
    parser.add_argument(
        "endpoint",
        type=str,
        help="PTP endpoint name (e.g., 'Submissions-Current-Operating-Plan')",
    )
    parser.add_argument(
        "--resource-filter",
        type=str,
        default="BEXAR",
        help="Resource name to filter for (default: 'BEXAR')",
    )
    parser.add_argument(
        "--entity-id",
        type=str,
        default=BEXAR_ENTITY_ID,
        help=f"Entity ID to test (default: {BEXAR_ENTITY_ID})",
    )
    parser.add_argument(
        "--generator-id",
        type=str,
        default=BEXAR_GENERATOR_ID,
        help=f"Generator ID to test (default: {BEXAR_GENERATOR_ID})",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip schema analysis test",
    )
    parser.add_argument(
        "--skip-viewport",
        action="store_true",
        help="Skip viewport test",
    )

    args = parser.parse_args()
    endpoint = args.endpoint
    resource_filter = args.resource_filter
    entity_id = args.entity_id
    generator_id = args.generator_id

    print("=" * 80)
    print("PTP Endpoint Parameter Testing")
    print("=" * 80)
    print(f"Endpoint: {endpoint}")
    print(f"Resource Filter: {resource_filter}")
    print(f"Entity ID: {entity_id}")
    print(f"Generator ID: {generator_id}")
    print("=" * 80)

    # Initialize token manager
    token_manager = get_tps_token_manager()
    token = await token_manager.get_token()

    # Test 1: Query without elements to find all identifiers
    test1_result = await test_without_elements(token, endpoint, resource_filter)

    # Find best identifier
    best_identifier = None
    if test1_result.get("success") and test1_result.get("bexar_entries"):
        bexar_entries = test1_result["bexar_entries"]
        # Find entry with most intervals
        best_entry = max(
            bexar_entries, key=lambda x: x.get("interval_count", 0), default=None
        )
        if best_entry and best_entry.get("has_data"):
            best_identifier = best_entry["identifier"]
            print(
                f"\n✅ Best identifier found: {best_identifier} "
                f"(Resource: {best_entry['resource_id']}, "
                f"Intervals: {best_entry['interval_count']})"
            )
        elif bexar_entries:
            # Use first entry even if no data yet
            best_identifier = bexar_entries[0]["identifier"]
            print(f"\n⚠️  Using identifier: {best_identifier} (no data found yet)")

    # If no identifier found, try known IDs
    if not best_identifier:
        print(f"\n⚠️  No {resource_filter} identifier found, testing known IDs...")
        best_identifier = entity_id

    # Test 2-9: Test with all Bexar identifiers iteratively
    print("\n" + "=" * 80)
    print("TEST: Iterative Testing of All Bexar Identifiers")
    print(f"Endpoint: {endpoint}")
    print("=" * 80)

    identifier_results = []
    for bexar_id_info in ALL_BEXAR_IDENTIFIERS:
        identifier_id = bexar_id_info["id"]
        identifier_name = bexar_id_info["name"]
        identifier_type = bexar_id_info["type"]

        print(f"\n  Testing: {identifier_name} ({identifier_type})")
        print(f"    ID: {identifier_id}")

        result = await test_with_element_id(
            token,
            endpoint,
            identifier_id,
            f"{identifier_name} ({identifier_type})",
            verbose=False,  # Compact output for iterative testing
        )

        identifier_results.append(
            {
                "identifier": identifier_id,
                "name": identifier_name,
                "type": identifier_type,
                "result": result,
            }
        )

    # Summary of all identifier tests
    print("\n" + "=" * 80)
    print("SUMMARY: All Bexar Identifier Test Results")
    print("=" * 80)

    best_from_all = None
    best_interval_count = 0
    best_name = None

    for id_result in identifier_results:
        result = id_result["result"]
        identifier_id = id_result["identifier"]
        identifier_name = id_result["name"]
        identifier_type = id_result["type"]

        if result.get("has_data") and result.get("data_fields"):
            total_intervals = sum(
                field.get("intervals", 0) for field in result.get("data_fields", [])
            )
            print(
                f"\n✅ {identifier_name} ({identifier_type}): "
                f"{len(result.get('data_fields', []))} fields, "
                f"{total_intervals} intervals"
            )
            if total_intervals > best_interval_count:
                best_interval_count = total_intervals
                best_from_all = identifier_id
                best_name = identifier_name
        else:
            print(f"\n❌ {identifier_name} ({identifier_type}): No data")

    if best_from_all:
        best_identifier = best_from_all
        print(
            f"\n🏆 Best identifier: {best_name} ({best_identifier}) "
            f"with {best_interval_count} total intervals"
        )
    elif not best_identifier:
        best_identifier = entity_id
        print(f"\n⚠️  No identifier with data found, using default: {entity_id}")

    # Test 5: Test with operating day range
    await test_operating_day_range(token, endpoint, best_identifier)

    # Test 6: Test different date ranges
    await test_different_date_ranges(token, endpoint, best_identifier)

    # Test 7: Endpoint schema
    if not args.skip_schema:
        await test_endpoint_schema(token, endpoint)

    # Test 8: Test with environment parameter
    await test_with_environment(token, endpoint, best_identifier)

    # Test 9: Test with viewport
    if not args.skip_viewport:
        await test_with_viewport(token, endpoint)

    # Test 10: Query all identifiers individually
    await test_query_all_identifiers(token, endpoint, resource_filter)

    # Test 11: Full structure analysis
    await analyze_data_structure(token, endpoint, best_identifier)

    print("\n" + "=" * 80)
    print("Testing Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_test_ptp_endpoint_cli())
