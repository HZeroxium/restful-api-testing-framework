#!/usr/bin/env python3
"""
Test script for the aggregator endpoint.
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def test_server_health():
    """Test if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False


def test_aggregator_endpoint():
    """Test the aggregator endpoint with get_brands."""
    print("\n=== Testing Aggregator Endpoint ===")

    endpoint_name = "get_brands"

    try:
        print(f"Testing POST /api/v1/aggregator/constraints-scripts/{endpoint_name}")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/api/v1/aggregator/constraints-scripts/{endpoint_name}",
            timeout=120,  # 2 minutes timeout for the aggregated operation
        )

        total_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Aggregator endpoint successful")
            print(f"   - Endpoint: {data.get('endpoint_name')}")
            print(f"   - Endpoint ID: {data.get('endpoint_id')}")
            print(f"   - Total constraints: {data.get('total_constraints')}")
            print(f"   - Total scripts: {data.get('total_scripts')}")
            print(
                f"   - Deleted constraints: {data.get('deleted_constraints_count', 0)}"
            )
            print(f"   - Deleted scripts: {data.get('deleted_scripts_count', 0)}")
            print(f"   - Total execution time: {data.get('total_execution_time'):.2f}s")
            print(f"   - Overall success: {data.get('overall_success')}")
            print(
                f"   - Constraints mining success: {data.get('constraints_mining_success')}"
            )
            print(
                f"   - Scripts generation success: {data.get('scripts_generation_success')}"
            )

            # Check for errors
            if data.get("constraints_error"):
                print(f"   - Constraints error: {data.get('constraints_error')}")
            if data.get("scripts_error"):
                print(f"   - Scripts error: {data.get('scripts_error')}")

            # Show constraint details
            constraints_result = data.get("constraints_result", {})
            print(f"\n   📊 Constraint Mining Results:")
            print(
                f"      - Request param constraints: {len(constraints_result.get('request_param_constraints', []))}"
            )
            print(
                f"      - Request body constraints: {len(constraints_result.get('request_body_constraints', []))}"
            )
            print(
                f"      - Response property constraints: {len(constraints_result.get('response_property_constraints', []))}"
            )
            print(
                f"      - Request-response constraints: {len(constraints_result.get('request_response_constraints', []))}"
            )

            # Show script details
            scripts_result = data.get("scripts_result", {})
            scripts = scripts_result.get("scripts", [])
            print(f"\n   📜 Validation Scripts Results:")
            print(f"      - Total scripts: {len(scripts)}")

            # Group scripts by type
            script_types = {}
            for script in scripts:
                script_type = script.get("script_type", "unknown")
                script_types[script_type] = script_types.get(script_type, 0) + 1

            for script_type, count in script_types.items():
                print(f"      - {script_type}: {count} scripts")

            print(f"\n   ⏱️  Performance:")
            print(f"      - Client time: {total_time:.2f}s")
            print(f"      - Server time: {data.get('total_execution_time', 0):.2f}s")

            return True

        elif response.status_code == 404:
            print(f"❌ Endpoint '{endpoint_name}' not found")
            print(f"   Response: {response.text}")
            return False

        else:
            print(f"❌ Aggregator endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Aggregator endpoint error: {e}")
        return False


def test_nonexistent_endpoint():
    """Test the aggregator endpoint with a non-existent endpoint."""
    print("\n=== Testing Aggregator with Non-existent Endpoint ===")

    endpoint_name = "nonexistent_endpoint"

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/aggregator/constraints-scripts/{endpoint_name}",
            timeout=30,
        )

        if response.status_code == 404:
            print(f"✅ Correctly returned 404 for non-existent endpoint")
            return True
        else:
            print(f"❌ Expected 404 but got {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error testing non-existent endpoint: {e}")
        return False


def test_individual_endpoints_comparison():
    """Test individual endpoints to compare with aggregator."""
    print("\n=== Testing Individual Endpoints for Comparison ===")

    endpoint_name = "get_brands"
    individual_results = {}

    # Test constraint mining
    try:
        print("Testing individual constraint mining...")
        response = requests.post(
            f"{BASE_URL}/api/v1/constraints/mine/by-endpoint-name/{endpoint_name}",
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            individual_results["constraints"] = {
                "total": data.get("total_constraints", 0),
                "success": True,
            }
            print(
                f"   ✅ Individual constraint mining: {data.get('total_constraints', 0)} constraints"
            )
        else:
            individual_results["constraints"] = {"success": False}
            print(f"   ❌ Individual constraint mining failed: {response.status_code}")

    except Exception as e:
        individual_results["constraints"] = {"success": False}
        print(f"   ❌ Individual constraint mining error: {e}")

    # Test script generation
    try:
        print("Testing individual script generation...")
        response = requests.post(
            f"{BASE_URL}/api/v1/validation-scripts/generate/by-endpoint-name/{endpoint_name}",
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            individual_results["scripts"] = {
                "total": data.get("total_scripts", 0),
                "success": True,
            }
            print(
                f"   ✅ Individual script generation: {data.get('total_scripts', 0)} scripts"
            )
        else:
            individual_results["scripts"] = {"success": False}
            print(f"   ❌ Individual script generation failed: {response.status_code}")

    except Exception as e:
        individual_results["scripts"] = {"success": False}
        print(f"   ❌ Individual script generation error: {e}")

    return individual_results


def main():
    """Main test function."""
    print("Testing Aggregator Endpoint")
    print("=" * 50)

    # Check server health
    if not test_server_health():
        return

    # Test individual endpoints first for comparison
    individual_results = test_individual_endpoints_comparison()

    # Test aggregator endpoint
    aggregator_success = test_aggregator_endpoint()

    # Test error handling
    error_handling_success = test_nonexistent_endpoint()

    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"✅ Server health: OK")
    print(
        f"✅ Individual constraint mining: {'OK' if individual_results.get('constraints', {}).get('success') else 'FAILED'}"
    )
    print(
        f"✅ Individual script generation: {'OK' if individual_results.get('scripts', {}).get('success') else 'FAILED'}"
    )
    print(f"✅ Aggregator endpoint: {'OK' if aggregator_success else 'FAILED'}")
    print(f"✅ Error handling: {'OK' if error_handling_success else 'FAILED'}")

    if aggregator_success and error_handling_success:
        print("\n🎉 All tests passed! Aggregator endpoint is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the logs above.")


if __name__ == "__main__":
    main()
