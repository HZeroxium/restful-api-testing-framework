#!/usr/bin/env python3
"""
Test script to verify the improvements to validation script generation and verification.
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def test_endpoint_health():
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


def test_constraint_mining():
    """Test constraint mining for get_brands endpoint."""
    print("\n=== Testing Constraint Mining ===")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/constraints/mine/by-endpoint-name/get_brands",
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Constraint mining successful")
            print(f"   - Total constraints: {data.get('total_constraints', 0)}")
            print(
                f"   - Request param constraints: {len(data.get('request_param_constraints', []))}"
            )
            print(
                f"   - Response property constraints: {len(data.get('response_property_constraints', []))}"
            )
            return True
        else:
            print(f"❌ Constraint mining failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Constraint mining error: {e}")
        return False


def test_validation_script_generation():
    """Test validation script generation."""
    print("\n=== Testing Validation Script Generation ===")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/validation-scripts/generate/by-endpoint-name/get_brands",
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Validation script generation successful")
            print(f"   - Total scripts: {data.get('total_scripts', 0)}")

            # Check if scripts use .get() syntax
            scripts = data.get("scripts", [])
            for script in scripts:
                code = script.get("validation_code", "")
                if "response.status_code" in code:
                    print(
                        f"   ⚠️  Script {script.get('name')} still uses response.status_code"
                    )
                elif "response.get(" in code:
                    print(
                        f"   ✅ Script {script.get('name')} uses response.get() syntax"
                    )

            return True
        else:
            print(f"❌ Validation script generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Validation script generation error: {e}")
        return False


def test_verification_endpoints():
    """Test the verification endpoints with improved error handling."""
    print("\n=== Testing Verification Endpoints ===")

    # Test data for verification
    test_data_items = [
        {
            "request_params": {"general": "true"},
            "request_headers": {},
            "request_body": None,
            "expected_status_code": 200,
        },
        {
            "request_params": {},
            "request_headers": {},
            "request_body": None,
            "expected_status_code": 200,
        },
    ]

    request_response_pairs = [
        {
            "request": {
                "method": "GET",
                "url": "http://localhost:8000/brands",
                "headers": {},
                "params": {"general": "true"},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": [
                    {"id": "brand1", "name": "Brand 1", "slug": "brand-1"},
                    {"id": "brand2", "name": "Brand 2", "slug": "brand-2"},
                ],
            },
        },
        {
            "request": {
                "method": "GET",
                "url": "http://localhost:8000/brands",
                "headers": {},
                "params": {},
                "body": None,
            },
            "response": {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": [{"id": "brand1", "name": "Brand 1", "slug": "brand-1"}],
            },
        },
    ]

    # Test test data verification
    print("Testing test data verification...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/verify/test-data/by-endpoint-name/get_brands",
            json={"test_data_items": test_data_items, "timeout": 30},
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test data verification successful")
            print(f"   - Total items: {data.get('total_test_data_items', 0)}")
            print(f"   - Overall passed: {data.get('overall_passed', False)}")

            # Check error messages
            for i, result in enumerate(data.get("verification_results", [])):
                print(
                    f"   - Test data {i}: {'✅ PASSED' if result.get('overall_passed') else '❌ FAILED'}"
                )
                for script_result in result.get("results", []):
                    if script_result.get("error_message"):
                        print(f"     Error: {script_result['error_message']}")
                    if script_result.get("script_output"):
                        print(f"     Output: {script_result['script_output'].strip()}")
        else:
            print(f"❌ Test data verification failed: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Test data verification error: {e}")

    # Test request-response verification
    print("\nTesting request-response verification...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/verify/request-response/get_brands",
            json={"request_response_pairs": request_response_pairs, "timeout": 30},
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Request-response verification successful")
            print(f"   - Total pairs: {data.get('total_pairs', 0)}")
            print(f"   - Overall passed: {data.get('overall_passed', False)}")

            # Check error messages
            for i, result in enumerate(data.get("verification_results", [])):
                print(
                    f"   - Pair {i}: {'✅ PASSED' if result.get('overall_passed') else '❌ FAILED'}"
                )
                for script_result in result.get("results", []):
                    if script_result.get("error_message"):
                        print(f"     Error: {script_result['error_message']}")
                    if script_result.get("script_output"):
                        print(f"     Output: {script_result['script_output'].strip()}")
        else:
            print(f"❌ Request-response verification failed: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Request-response verification error: {e}")


def test_export_validation_scripts():
    """Test exporting validation scripts to Python file."""
    print("\n=== Testing Export Validation Scripts ===")

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/validation-scripts/to-python-file/get_brands",
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Export successful")
            print(f"   - Scripts exported: {data.get('scripts_count', 0)}")
            print(f"   - File path: {data.get('file_path', '')}")

            # Check if the exported file uses .get() syntax
            try:
                with open(data.get("file_path", ""), "r") as f:
                    content = f.read()
                    if "response.status_code" in content:
                        print("   ⚠️  Exported file still contains response.status_code")
                    elif "response.get(" in content:
                        print("   ✅ Exported file uses response.get() syntax")
            except Exception as e:
                print(f"   ⚠️  Could not check exported file: {e}")

            return True
        else:
            print(f"❌ Export failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False


def main():
    """Main test function."""
    print("Testing Verification Improvements")
    print("=" * 50)

    # Check server health
    if not test_endpoint_health():
        return

    # Run tests
    test_constraint_mining()
    test_validation_script_generation()
    test_verification_endpoints()
    test_export_validation_scripts()

    print("\n" + "=" * 50)
    print("Testing completed!")


if __name__ == "__main__":
    main()
