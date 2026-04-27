#!/usr/bin/env python3
"""Comprehensive exploration of PTP API structure for Bexar project.

This script explores the PowerTools Platform API to understand:
1. Available markets
2. Available endpoints per market
3. Schema information for each endpoint
4. Available elements (identifiers) per endpoint
5. Data structure and content for Bexar project
"""

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add the api directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.dependencies import get_async_db
from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import get_tps_token_manager
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def find_bexar_project_info(db: AsyncSession) -> dict | None:
    """Find the Bexar project and return its information.

    Args:
        db: Async database session.

    Returns:
        Mapping of basic Bexar project fields, or None if not found.
    """
    print("🔍 Searching for Bexar project in database...")

    query = select(models.Project).where(
        func.lower(models.Project.name_short) == "bexar"
    )
    result = await db.execute(query)
    project = result.scalar_one_or_none()

    if project is None:
        print("   Trying name_long...")
        query = select(models.Project).where(
            func.lower(models.Project.name_long).contains("bexar")
        )
        result = await db.execute(query)
        project = result.scalar_one_or_none()

    if project is None:
        print("❌ Bexar project not found in database")
        return None

    print("✅ Found Bexar project:")
    print(f"   Project ID: {project.project_id}")
    print(f"   Name Short: {project.name_short}")
    print(f"   Name Long: {project.name_long}")

    # Get QSE integration
    qse_query = select(models.QSEIntegration).where(
        models.QSEIntegration.project_id == project.project_id
    )
    qse_result = await db.execute(qse_query)
    qse_integration = qse_result.scalar_one_or_none()

    if qse_integration is None:
        print("❌ No QSE integration found for Bexar project")
        return None

    identifier = qse_integration.qse_project_identifier
    print("✅ Found QSE integration:")
    print(f"   QSE Project Identifier: {identifier}")

    return {
        "project_id": str(project.project_id),
        "name_short": project.name_short,
        "name_long": project.name_long,
        "qse_identifier": identifier,
    }


async def explore_markets(token: str) -> dict:
    """Explore all available markets.

    Args:
        token: TPS bearer token.

    Returns:
        Mapping of market name to identifier + raw payload.
    """
    print("\n" + "=" * 80)
    print("📊 EXPLORING MARKETS")
    print("=" * 80)

    try:
        markets_response = await ptp_explorer.get_markets(token=token)

        if "data" in markets_response:
            markets = markets_response["data"]
            print(f"\n✅ Found {len(markets)} market(s):")

            market_info = {}
            for market in markets:
                market_name = market.get("name") or market.get("identifier", "Unknown")
                market_id = market.get("identifier", "Unknown")
                print(f"\n   Market: {market_name}")
                print(f"   Identifier: {market_id}")
                print(f"   Full data: {json.dumps(market, indent=6)}")

                market_info[market_name] = {
                    "identifier": market_id,
                    "raw": market,
                }

            return market_info
        else:
            print("⚠️  Unexpected response structure:")
            print(json.dumps(markets_response, indent=2))
            return {}
    except Exception as e:
        print(f"❌ Error fetching markets: {e}")
        import traceback

        traceback.print_exc()
        return {}


async def explore_endpoints(token: str, market: str) -> dict:
    """Explore all endpoints for a market.

    Args:
        token: TPS bearer token.
        market: Market name/identifier.

    Returns:
        Mapping of endpoint name to identifier + raw payload.
    """
    print("\n" + "=" * 80)
    print(f"📋 EXPLORING ENDPOINTS FOR MARKET: {market}")
    print("=" * 80)

    try:
        endpoints_response = await ptp_explorer.get_endpoints(
            token=token, market=market
        )

        if "data" in endpoints_response:
            endpoints = endpoints_response["data"]
            print(f"\n✅ Found {len(endpoints)} endpoint(s):")

            endpoint_info = {}
            for endpoint in endpoints:
                endpoint_name = endpoint.get("name") or endpoint.get(
                    "identifier", "Unknown"
                )
                endpoint_id = endpoint.get("identifier", "Unknown")
                print(f"\n   Endpoint: {endpoint_name}")
                print(f"   Identifier: {endpoint_id}")

                endpoint_info[endpoint_name] = {
                    "identifier": endpoint_id,
                    "raw": endpoint,
                }

            return endpoint_info
        else:
            print("⚠️  Unexpected response structure:")
            print(json.dumps(endpoints_response, indent=2))
            return {}
    except Exception as e:
        print(f"❌ Error fetching endpoints: {e}")
        import traceback

        traceback.print_exc()
        return {}


async def explore_endpoint_schema(token: str, market: str, endpoint: str) -> dict:
    """Explore schema for a specific endpoint.

    Args:
        token: TPS bearer token.
        market: Market name/identifier.
        endpoint: Endpoint name/identifier.

    Returns:
        Schema payload (and extracted summaries).
    """
    print(f"\n   📐 Schema for endpoint: {endpoint}")

    try:
        schema_response = await ptp_explorer.get_endpoint_schema(
            token=token, market=market, endpoint=endpoint
        )

        # Extract key schema information
        schema_info = {
            "raw": schema_response,
        }

        # Look for dataPoints in schema
        data_points = None
        if "data" in schema_response:
            if (
                isinstance(schema_response["data"], dict)
                and "dataPoints" in schema_response["data"]
            ):
                data_points = schema_response["data"]["dataPoints"]
            elif isinstance(schema_response["data"], list):
                data_points = schema_response["data"]
        elif "dataPoints" in schema_response:
            data_points = schema_response["dataPoints"]

        if data_points:
            print(f"      Found {len(data_points)} data point(s) in schema:")
            schema_info["data_points"] = []
            for dp in data_points:
                if isinstance(dp, dict):
                    key_name = (
                        dp.get("keyName")
                        or dp.get("name")
                        or dp.get("identifier", "Unknown")
                    )
                    data_type = dp.get("dataType") or dp.get("type") or "Unknown"
                    dp_type = dp.get("dataPointType") or dp.get("type") or "Unknown"
                    print(
                        f"         - {key_name} (Type: {data_type}, DP Type: {dp_type})"
                    )
                    schema_info["data_points"].append(
                        {
                            "keyName": key_name,
                            "dataType": data_type,
                            "dataPointType": dp_type,
                            "raw": dp,
                        }
                    )

        # Look for element definitions
        element_defs = None
        if "data" in schema_response:
            if (
                isinstance(schema_response["data"], dict)
                and "elementDefinitions" in schema_response["data"]
            ):
                element_defs = schema_response["data"]["elementDefinitions"]
        elif "elementDefinitions" in schema_response:
            element_defs = schema_response["elementDefinitions"]

        if element_defs:
            print(f"      Found {len(element_defs)} element definition(s):")
            schema_info["element_definitions"] = []
            for ed in element_defs:
                if isinstance(ed, dict):
                    ed_name = ed.get("name") or ed.get("identifier", "Unknown")
                    print(f"         - {ed_name}")
                    schema_info["element_definitions"].append(
                        {
                            "name": ed_name,
                            "raw": ed,
                        }
                    )

        return schema_info
    except Exception as e:
        print(f"      ❌ Error fetching schema: {e}")
        return {"error": str(e)}


async def explore_endpoint_elements(
    token: str, market: str, endpoint: str, bexar_identifier: str = None
) -> dict:
    """Explore available elements for an endpoint.

    Args:
        token: TPS bearer token.
        market: Market name/identifier.
        endpoint: Endpoint name/identifier.
        bexar_identifier: Optional identifier to search for.

    Returns:
        Elements payload (and extracted summaries).
    """
    print(f"\n   🔍 Elements for endpoint: {endpoint}")

    try:
        elements_response = await ptp_explorer.get_endpoint_elements(
            token=token, market=market, endpoint=endpoint
        )

        elements_info = {
            "raw": elements_response,
        }

        if "data" in elements_response:
            elements = elements_response["data"]
            print(f"      Found {len(elements)} element(s)")

            # Check if it's a list of strings or list of objects
            if elements and isinstance(elements[0], str):
                elements_list = elements
                elements_info["elements"] = elements_list

                # Check for Bexar identifier
                if bexar_identifier:
                    if bexar_identifier in elements_list:
                        print(f"      ✅ Bexar identifier '{bexar_identifier}' found!")
                        elements_info["bexar_found"] = True
                    else:
                        print(
                            f"      ⚠️  Bexar identifier '{bexar_identifier}' not found"
                        )
                        # Look for similar identifiers
                        bexar_candidates = [
                            e
                            for e in elements_list
                            if "BEXAR" in e.upper()
                            or bexar_identifier.upper() in e.upper()
                        ]
                        if bexar_candidates:
                            print(
                                f"      Found {len(bexar_candidates)} similar "
                                "identifier(s):"
                            )
                            for candidate in bexar_candidates[:5]:
                                print(f"         - {candidate}")
                            elements_info["bexar_candidates"] = bexar_candidates
                        elements_info["bexar_found"] = False

                # Show first 10 elements
                print("      First 10 elements:")
                for elem in elements[:10]:
                    print(f"         - {elem}")
            else:
                # List of objects
                elements_info["elements"] = [
                    e.get("name") or e.get("identifier", "Unknown")
                    for e in elements
                    if isinstance(e, dict)
                ]
                print("      Element objects (showing first 10):")
                for elem in elements[:10]:
                    if isinstance(elem, dict):
                        elem_name = elem.get("name") or elem.get(
                            "identifier", "Unknown"
                        )
                        print(f"         - {elem_name}")
        else:
            print("      ⚠️  Unexpected response structure")
            print(f"      Keys: {list(elements_response.keys())}")

        return elements_info
    except Exception as e:
        print(f"      ❌ Error fetching elements: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


async def explore_endpoint_data(
    token: str,
    market: str,
    endpoint: str,
    bexar_identifier: str = None,
    sample_only: bool = True,
) -> dict:
    """Explore data from an endpoint, optionally filtered by Bexar identifier.

    Args:
        token: TPS bearer token.
        market: Market name/identifier.
        endpoint: Endpoint name/identifier.
        bexar_identifier: Optional identifier to filter elements.
        sample_only: If True, print a small sample of data points.

    Returns:
        Data payload (and extracted summaries).
    """
    print(f"\n   📥 Data for endpoint: {endpoint}")

    try:
        # Use a recent time range (last 7 days to future 2 hours)
        now = datetime.now(UTC)
        begin = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
        end = (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z")

        # First, try to get all data (or filtered by Bexar if provided)
        elements_filter = [bexar_identifier] if bexar_identifier else None

        data_response = await ptp_explorer.get_endpoint_data(
            token=token,
            market=market,
            endpoint=endpoint,
            elements=elements_filter,
            begin=begin,
            end=end,
        )

        data_info = {
            "raw": data_response,
            "time_range": {"begin": begin, "end": end},
        }

        if "data" in data_response:
            entries = data_response["data"]
            print(f"      Found {len(entries)} data entry/entries")
            data_info["entry_count"] = len(entries)

            if entries:
                # Analyze first entry structure
                first_entry = entries[0]
                print("\n      📊 First entry structure:")
                print(f"         Identifier: {first_entry.get('identifier', 'N/A')}")
                print(f"         Element: {first_entry.get('element', 'N/A')}")
                print(f"         Definition: {first_entry.get('definition', 'N/A')}")

                data_points = first_entry.get("dataPoints", [])
                print(f"         Data Points: {len(data_points)}")

                data_info["sample_entry"] = {
                    "identifier": first_entry.get("identifier"),
                    "element": first_entry.get("element"),
                    "definition": first_entry.get("definition"),
                    "data_points_count": len(data_points),
                }

                # Show data point summary
                print("\n      📋 Data Points Summary:")
                dp_iter = data_points[:10] if sample_only else data_points
                for dp in dp_iter:
                    key_name = dp.get("keyName", "Unknown")
                    values = dp.get("values", [])
                    print(f"         - {key_name}: {len(values)} value(s)")

                    # Show first value if available
                    if values and isinstance(values[0], dict):
                        first_val = values[0]
                        interval_start = first_val.get("intervalStartUtc", "N/A")
                        interval_end = first_val.get("intervalEndUtc", "N/A")
                        value_data = first_val.get("data", [])
                        if value_data:
                            value = (
                                value_data[0].get("value", "N/A")
                                if isinstance(value_data[0], dict)
                                else value_data[0]
                            )
                            print(
                                f"           First value: {value} (Interval: "
                                f"{interval_start} to {interval_end})"
                            )

                # Check for Bexar-related entries
                if bexar_identifier:
                    bexar_entries = [
                        e
                        for e in entries
                        if bexar_identifier in str(e.get("identifier", "")).upper()
                    ]
                    if bexar_entries:
                        print(
                            f"\n      ✅ Found {len(bexar_entries)} entry/entries "
                            "matching Bexar identifier"
                        )
                        data_info["bexar_entries"] = len(bexar_entries)
                    else:
                        # Look for Resource_ID matches
                        bexar_by_resource = []
                        for entry in entries:
                            data_points = entry.get("dataPoints", [])
                            for dp in data_points:
                                if dp.get("keyName") == "Resource_ID":
                                    values = dp.get("values", [])
                                    for val in values:
                                        if isinstance(val, dict):
                                            value_data = val.get("data", [])
                                            if value_data and len(value_data) > 0:
                                                resource_id = str(
                                                    value_data[0].get("value", "")
                                                )
                                                if "BEXAR" in resource_id.upper():
                                                    bexar_by_resource.append(
                                                        entry.get("identifier")
                                                    )
                                                    break

                        if bexar_by_resource:
                            print(
                                f"\n      ✅ Found {len(bexar_by_resource)} "
                                "entry/entries with BEXAR in Resource_ID"
                            )
                            print(f"         Identifiers: {bexar_by_resource[:5]}")
                            data_info["bexar_by_resource"] = bexar_by_resource
        else:
            print("      ⚠️  Unexpected response structure")
            print(f"      Keys: {list(data_response.keys())}")

        return data_info
    except Exception as e:
        print(f"      ❌ Error fetching data: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}


async def comprehensive_exploration(token: str, bexar_info: dict | None = None):
    """Perform comprehensive exploration of the PTP API.

    Args:
        token: TPS bearer token.
        bexar_info: Optional pre-fetched Bexar project info.
    """
    print("\n" + "=" * 80)
    print("🚀 COMPREHENSIVE PTP API EXPLORATION")
    print("=" * 80)

    # Step 1: Get all markets
    markets = await explore_markets(token)

    if not markets:
        print("\n❌ No markets found. Cannot continue exploration.")
        return

    # Step 2: For each market, explore endpoints
    all_results = {}

    for market_name, market_data in markets.items():
        print(f"\n\n{'=' * 80}")
        print(f"🔍 EXPLORING MARKET: {market_name}")
        print("=" * 80)

        endpoints = await explore_endpoints(token, market_name)
        all_results[market_name] = {
            "market_info": market_data,
            "endpoints": {},
        }

        # Step 3: For each endpoint, explore schema, elements, and data
        for endpoint_name, endpoint_data in endpoints.items():
            print(f"\n\n{'─' * 80}")
            print(f"🔬 DETAILED EXPLORATION: {endpoint_name}")
            print("─" * 80)

            endpoint_results = {
                "endpoint_info": endpoint_data,
                "schema": {},
                "elements": {},
                "data": {},
            }

            # Get schema
            schema_info = await explore_endpoint_schema(
                token, market_name, endpoint_name
            )
            endpoint_results["schema"] = schema_info

            # Get elements
            bexar_id = bexar_info.get("qse_identifier") if bexar_info else None
            elements_info = await explore_endpoint_elements(
                token, market_name, endpoint_name, bexar_id
            )
            endpoint_results["elements"] = elements_info

            # Get data (sample)
            data_info = await explore_endpoint_data(
                token, market_name, endpoint_name, bexar_id, sample_only=True
            )
            endpoint_results["data"] = data_info

            all_results[market_name]["endpoints"][endpoint_name] = endpoint_results

    # Print summary
    print("\n\n" + "=" * 80)
    print("📊 EXPLORATION SUMMARY")
    print("=" * 80)

    for market_name, market_results in all_results.items():
        print(f"\nMarket: {market_name}")
        print(f"  Endpoints: {len(market_results['endpoints'])}")

        for endpoint_name, endpoint_results in market_results["endpoints"].items():
            print(f"\n  Endpoint: {endpoint_name}")

            # Schema summary
            schema = endpoint_results.get("schema", {})
            if "data_points" in schema:
                print(f"    Data Points: {len(schema['data_points'])}")

            # Elements summary
            elements = endpoint_results.get("elements", {})
            if "elements" in elements:
                elem_list = elements["elements"]
                if isinstance(elem_list, list):
                    print(f"    Elements: {len(elem_list)}")
                    if "bexar_found" in elements:
                        print(f"    Bexar Found: {elements['bexar_found']}")

            # Data summary
            data = endpoint_results.get("data", {})
            if "entry_count" in data:
                print(f"    Data Entries: {data['entry_count']}")
                if "bexar_entries" in data:
                    print(f"    Bexar Entries: {data['bexar_entries']}")

    return all_results


async def run_ptp_api_structure_explorer():
    """Run the PTP API structure exploration CLI."""
    print("=" * 80)
    print("PTP API STRUCTURE EXPLORATION FOR BEXAR PROJECT")
    print("=" * 80)

    # Get database session
    async for db in get_async_db():
        try:
            # Find Bexar project
            bexar_info = await find_bexar_project_info(db)

            # Get token
            print("\n🔐 Getting token...")
            token_manager = get_tps_token_manager()
            token = await token_manager.get_token()
            print(f"✅ Token retrieved! (length: {len(token)} chars)")

            # Perform comprehensive exploration
            await comprehensive_exploration(token, bexar_info)

            print("\n✅ Exploration complete!")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
        finally:
            break  # Exit the async generator


if __name__ == "__main__":
    success = asyncio.run(run_ptp_api_structure_explorer())
    sys.exit(0 if success else 1)
