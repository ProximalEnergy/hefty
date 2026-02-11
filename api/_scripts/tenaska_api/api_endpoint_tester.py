#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml>=6.0"]
# ///
"""API Endpoint Tester using OpenAPI Specification (OAS).

This script allows you to test API endpoints and validate their responses
against OpenAPI specifications. It can work with:
- OpenAPI spec files (JSON/YAML)
- Direct API testing without specs
- PTP API endpoints

Usage:
    # Test a PTP endpoint
    uv run --script api_endpoint_tester.py ptp --market ERCOTNodal --endpoint
        Generator-Performance

    # Test with OpenAPI spec validation
    uv run --script api_endpoint_tester.py spec --spec-file openapi.json \
        --path /v1/projects

    # Test a direct API endpoint
    uv run --script api_endpoint_tester.py direct --url
        https://api.example.com/v1/data --method GET
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

# Add the api directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.providers import ptp_explorer
from app.integrations.token_manager import get_tps_token_manager


def _load_yaml_module() -> Any:
    try:
        import importlib

        module_name = "yaml"
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        message = (
            "PyYAML is required for YAML files. Run: "
            "uv run --script api_endpoint_tester.py ..."
        )
        raise RuntimeError(message) from exc


class APIEndpointTester:
    """Test API endpoints and validate responses."""

    def __init__(self, *, verbose: bool = False):
        """Initialize the tester.

        Args:
            verbose: Enable verbose output.
        """
        self.verbose = verbose
        self.results: list[dict[str, Any]] = []

    async def test_ptp_endpoint(
        self,
        *,
        market: str = "ERCOTNodal",
        endpoint: str,
        elements: list[str] | None = None,
        begin: str | None = None,
        end: str | None = None,
        environment: str | None = None,
    ) -> dict[str, Any]:
        """Test a PTP API endpoint.

        Args:
            market: Market name (default: ERCOTNodal).
            endpoint: Endpoint name.
            elements: Optional list of element identifiers.
            begin: Optional begin timestamp (ISO 8601 UTC).
            end: Optional end timestamp (ISO 8601 UTC).
            environment: Optional environment filter.

        Returns:
            Test result dictionary.
        """
        print("=" * 80)
        print("PTP API Endpoint Tester")
        print("=" * 80)
        print(f"Market: {market}")
        print(f"Endpoint: {endpoint}")
        if elements:
            print(f"Elements: {elements}")
        if begin:
            print(f"Begin: {begin}")
        if end:
            print(f"End: {end}")
        print("=" * 80)

        token_manager = get_tps_token_manager()
        token = await token_manager.get_token()

        result: dict[str, Any] = {
            "type": "ptp",
            "market": market,
            "endpoint": endpoint,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            # Get endpoint schema first
            print("\n📋 Fetching endpoint schema...")
            schema = await ptp_explorer.get_endpoint_schema(
                token=token, market=market, endpoint=endpoint
            )
            result["schema"] = schema
            print("✅ Schema retrieved")

            # Get endpoint data
            print("\n📊 Fetching endpoint data...")
            data = await ptp_explorer.get_endpoint_data(
                token=token,
                market=market,
                endpoint=endpoint,
                elements=elements,
                begin=begin,
                end=end,
                environment=environment,
            )
            result["data"] = data
            result["success"] = True

            # Analyze response
            self._analyze_ptp_response(result)

            print("\n✅ Test completed successfully")
            return result

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"\n❌ Test failed: {e}")
            return result

    def _analyze_ptp_response(self, result: dict[str, Any]) -> None:
        """Analyze PTP API response and extract key information.

        Args:
            result: Result dictionary to update with analysis.
        """
        data = result.get("data", {})
        analysis: dict[str, Any] = {}

        # Count elements
        if "data" in data:
            elements = data["data"]
            analysis["element_count"] = len(elements)
            print(f"\n📈 Found {len(elements)} elements")

            # Analyze first element if available
            if elements:
                first_element = elements[0]
                analysis["first_element"] = {
                    "identifier": first_element.get("identifier"),
                    "element": first_element.get("element"),
                    "definition": first_element.get("definition"),
                }

                # Count data points
                data_points = first_element.get("dataPoints", [])
                analysis["data_point_count"] = len(data_points)
                print(f"📊 Found {len(data_points)} data points")

                # Show sample data points
                if data_points and self.verbose:
                    print("\n📋 Sample Data Points:")
                    for i, dp in enumerate(data_points[:5]):
                        print(f"  {i + 1}. {dp.get('keyName', 'N/A')}")

                # Analyze values
                if data_points:
                    total_values = 0
                    for dp in data_points:
                        values = dp.get("values", [])
                        total_values += len(values)
                    analysis["total_value_count"] = total_values
                    print(f"📈 Total values: {total_values}")

        result["analysis"] = analysis

    async def test_openapi_endpoint(
        self,
        *,
        spec_file: str,
        path: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        base_url: str | None = None,
    ) -> dict[str, Any]:
        """Test an endpoint using OpenAPI specification.

        Args:
            spec_file: Path to OpenAPI spec file (JSON or YAML).
            path: API path to test.
            method: HTTP method (default: GET).
            params: Query parameters.
            headers: Additional headers.
            base_url: Base URL (if not in spec).

        Returns:
            Test result dictionary.
        """
        print("=" * 80)
        print("OpenAPI Endpoint Tester")
        print("=" * 80)
        print(f"Spec File: {spec_file}")
        print(f"Path: {path}")
        print(f"Method: {method}")
        print("=" * 80)

        result: dict[str, Any] = {
            "type": "openapi",
            "spec_file": spec_file,
            "path": path,
            "method": method,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            # Load OpenAPI spec
            print("\n📋 Loading OpenAPI specification...")
            spec = self._load_openapi_spec(spec_file)
            result["spec"] = spec

            # Find endpoint in spec
            endpoint_info = self._find_endpoint_in_spec(spec, path, method)
            if not endpoint_info:
                raise ValueError(f"Endpoint {method} {path} not found in OpenAPI spec")

            result["endpoint_info"] = endpoint_info
            print(f"✅ Found endpoint: {endpoint_info.get('summary', 'N/A')}")

            # Get base URL
            if not base_url:
                servers = spec.get("servers", [])
                if servers:
                    base_url = servers[0].get("url", "")
                else:
                    raise ValueError("No base URL found in spec or provided")

            # Build full URL
            full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
            result["url"] = full_url

            # Make request
            print(f"\n🌐 Making {method} request to {full_url}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=full_url,
                    params=params,
                    headers=headers,
                )

                result["response"] = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else response.text,
                }

                # Validate response
                self._validate_openapi_response(result, endpoint_info, response)

                result["success"] = response.is_success
                print(
                    f"✅ Response received: {response.status_code} "
                    f"{response.reason_phrase}"
                )

            return result

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"\n❌ Test failed: {e}")
            return result

    def _load_openapi_spec(self, spec_file: str) -> dict[str, Any]:
        """Load OpenAPI specification from file.

        Args:
            spec_file: Path to spec file.

        Returns:
            Parsed OpenAPI spec dictionary.
        """
        path = Path(spec_file)
        if not path.exists():
            raise FileNotFoundError(f"Spec file not found: {spec_file}")

        with path.open() as f:
            if path.suffix in [".yaml", ".yml"]:
                yaml_module = _load_yaml_module()
                return yaml_module.safe_load(f)
            return json.load(f)

    def _find_endpoint_in_spec(
        self, spec: dict[str, Any], path: str, method: str
    ) -> dict[str, Any] | None:
        """Find endpoint definition in OpenAPI spec.

        Args:
            spec: OpenAPI spec dictionary.
            path: API path.
            method: HTTP method.

        Returns:
            Endpoint definition or None.
        """
        paths = spec.get("paths", {})
        method_lower = method.lower()

        # Try exact match first
        if path in paths:
            endpoint = paths[path]
            if method_lower in endpoint:
                return endpoint[method_lower]

        # Try path matching (simplified)
        for spec_path, path_item in paths.items():
            if self._paths_match(spec_path, path):
                if method_lower in path_item:
                    return path_item[method_lower]

        return None

    def _paths_match(self, spec_path: str, request_path: str) -> bool:
        """Check if OpenAPI path matches request path.

        Args:
            spec_path: Path from OpenAPI spec (may have parameters).
            request_path: Actual request path.

        Returns:
            True if paths match.
        """
        # Simple matching - could be enhanced with proper parameter parsing
        spec_parts = spec_path.split("/")
        request_parts = request_path.split("/")

        if len(spec_parts) != len(request_parts):
            return False

        for spec_part, request_part in zip(spec_parts, request_parts):
            if spec_part.startswith("{") and spec_part.endswith("}"):
                continue  # Parameter placeholder
            if spec_part != request_part:
                return False

        return True

    def _validate_openapi_response(
        self,
        result: dict[str, Any],
        endpoint_info: dict[str, Any],
        response: httpx.Response,
    ) -> None:
        """Validate response against OpenAPI spec.

        Args:
            result: Result dictionary to update.
            endpoint_info: Endpoint definition from spec.
            response: HTTP response.
        """
        validation: dict[str, Any] = {
            "status_code_valid": False,
            "content_type_valid": False,
        }

        # Check status code
        responses = endpoint_info.get("responses", {})
        status_str = str(response.status_code)
        if status_str in responses:
            validation["status_code_valid"] = True
            validation["expected_status"] = status_str

        # Check content type
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            validation["content_type_valid"] = True

        result["validation"] = validation

    async def test_direct_endpoint(
        self,
        *,
        url: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Test an endpoint directly without OpenAPI spec.

        Args:
            url: Full URL to test.
            method: HTTP method (default: GET).
            params: Query parameters.
            headers: Request headers.
            body: Request body (for POST/PUT).

        Returns:
            Test result dictionary.
        """
        print("=" * 80)
        print("Direct API Endpoint Tester")
        print("=" * 80)
        print(f"URL: {url}")
        print(f"Method: {method}")
        print("=" * 80)

        result: dict[str, Any] = {
            "type": "direct",
            "url": url,
            "method": method,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            print(f"\n🌐 Making {method} request...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=body,
                )

                result["response"] = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": (
                        response.json()
                        if response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else response.text
                    ),
                }

                result["success"] = response.is_success

                # Analyze response
                self._analyze_direct_response(result)

                print(
                    f"✅ Response received: {response.status_code} "
                    f"{response.reason_phrase}"
                )
                if self.verbose:
                    print("\n📄 Response body preview:")
                    body_preview = str(result["response"]["body"])[:500]
                    print(body_preview)
                    if len(str(result["response"]["body"])) > 500:
                        print("... (truncated)")

            return result

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"\n❌ Test failed: {e}")
            return result

    def _analyze_direct_response(self, result: dict[str, Any]) -> None:
        """Analyze direct API response.

        Args:
            result: Result dictionary to update.
        """
        response = result.get("response", {})
        body = response.get("body")

        analysis: dict[str, Any] = {
            "status_code": response.get("status_code"),
            "content_type": response.get("headers", {}).get("content-type"),
        }

        if isinstance(body, dict):
            analysis["response_type"] = "JSON object"
            analysis["keys"] = list(body.keys())
            analysis["key_count"] = len(body.keys())
        elif isinstance(body, list):
            analysis["response_type"] = "JSON array"
            analysis["item_count"] = len(body)
        elif isinstance(body, str):
            analysis["response_type"] = "Text"
            analysis["length"] = len(body)

        result["analysis"] = analysis

    def print_results(self, result: dict[str, Any]) -> None:
        """Print test results in a readable format.

        Args:
            result: Test result dictionary.
        """
        print("\n" + "=" * 80)
        print("Test Results Summary")
        print("=" * 80)

        print(f"\n✅ Success: {result.get('success', False)}")
        print(f"📅 Timestamp: {result.get('timestamp', 'N/A')}")

        if result.get("type") == "ptp":
            print(f"\n📊 Market: {result.get('market')}")
            print(f"🔗 Endpoint: {result.get('endpoint')}")

            analysis = result.get("analysis", {})
            if analysis:
                print("\n📈 Analysis:")
                print(f"  - Elements: {analysis.get('element_count', 0)}")
                print(f"  - Data Points: {analysis.get('data_point_count', 0)}")
                print(f"  - Total Values: {analysis.get('total_value_count', 0)}")

        elif result.get("type") == "openapi":
            print(f"\n📄 Spec File: {result.get('spec_file')}")
            print(f"🔗 Path: {result.get('path')}")
            print(f"🌐 URL: {result.get('url')}")

            validation = result.get("validation", {})
            if validation:
                print("\n✅ Validation:")
                print(f"  - Status Code Valid: {validation.get('status_code_valid')}")
                print(f"  - Content Type Valid: {validation.get('content_type_valid')}")

        elif result.get("type") == "direct":
            print(f"\n🌐 URL: {result.get('url')}")
            print(f"📡 Method: {result.get('method')}")

            analysis = result.get("analysis", {})
            if analysis:
                print("\n📈 Analysis:")
                print(f"  - Status Code: {analysis.get('status_code')}")
                print(f"  - Content Type: {analysis.get('content_type')}")
                print(f"  - Response Type: {analysis.get('response_type')}")

        if result.get("error"):
            print(f"\n❌ Error: {result['error']}")

        print("\n" + "=" * 80)


async def main():
    """Main function to run the endpoint tester."""
    parser = argparse.ArgumentParser(
        description="Test API endpoints using OpenAPI specs or direct testing"
    )
    subparsers = parser.add_subparsers(dest="mode", help="Testing mode")

    # PTP endpoint tester
    ptp_parser = subparsers.add_parser("ptp", help="Test PTP API endpoint")
    ptp_parser.add_argument(
        "--market",
        type=str,
        default="ERCOTNodal",
        help="Market name (default: ERCOTNodal)",
    )
    ptp_parser.add_argument(
        "--endpoint",
        type=str,
        required=True,
        help="Endpoint name (e.g., Generator-Performance)",
    )
    ptp_parser.add_argument(
        "--elements",
        type=str,
        nargs="+",
        help="Element identifiers to filter",
    )
    ptp_parser.add_argument(
        "--begin",
        type=str,
        help="Begin timestamp (ISO 8601 UTC)",
    )
    ptp_parser.add_argument(
        "--end",
        type=str,
        help="End timestamp (ISO 8601 UTC)",
    )
    ptp_parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days back from now (default: 1)",
    )

    # OpenAPI spec tester
    spec_parser = subparsers.add_parser("spec", help="Test endpoint using OpenAPI spec")
    spec_parser.add_argument(
        "--spec-file",
        type=str,
        required=True,
        help="Path to OpenAPI spec file (JSON or YAML)",
    )
    spec_parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="API path to test",
    )
    spec_parser.add_argument(
        "--method",
        type=str,
        default="GET",
        help="HTTP method (default: GET)",
    )
    spec_parser.add_argument(
        "--base-url",
        type=str,
        help="Base URL (if not in spec)",
    )

    # Direct endpoint tester
    direct_parser = subparsers.add_parser(
        "direct", help="Test endpoint directly without spec"
    )
    direct_parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Full URL to test",
    )
    direct_parser.add_argument(
        "--method",
        type=str,
        default="GET",
        help="HTTP method (default: GET)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        return

    tester = APIEndpointTester(verbose=args.verbose)

    if args.mode == "ptp":
        # Set default date range if not provided
        if not args.begin or not args.end:
            end_time = datetime.now(UTC)
            begin_time = end_time - timedelta(days=args.days)
            args.begin = begin_time.isoformat()
            args.end = end_time.isoformat()

        result = await tester.test_ptp_endpoint(
            market=args.market,
            endpoint=args.endpoint,
            elements=args.elements,
            begin=args.begin,
            end=args.end,
        )

    elif args.mode == "spec":
        result = await tester.test_openapi_endpoint(
            spec_file=args.spec_file,
            path=args.path,
            method=args.method,
            base_url=args.base_url,
        )

    elif args.mode == "direct":
        result = await tester.test_direct_endpoint(
            url=args.url,
            method=args.method,
        )

    tester.print_results(result)


if __name__ == "__main__":
    asyncio.run(main())
