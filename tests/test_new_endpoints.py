"""
Test script for new endpoints:
- DELETE /validation-scripts/by-endpoint-name/{endpoint_name}
- DELETE /constraints/by-endpoint-name/{endpoint_name}
- POST /validation-scripts/to-python-file/{endpoint_name}
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"


def test_export_scripts_to_python():
    """Test exporting validation scripts to Python file."""
    print("\n=== Testing POST /validation-scripts/to-python-file/get_brands ===")
    endpoint_name = "get_brands"
    url = f"{BASE_URL}/validation-scripts/to-python-file/{endpoint_name}"

    response = requests.post(url)

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print("✅ Script export successful!")
    else:
        print(f"❌ Script export failed: {response.text}")

    return response


def test_delete_validation_scripts():
    """Test deleting validation scripts by endpoint name."""
    print("\n=== Testing DELETE /validation-scripts/by-endpoint-name/get_brands ===")
    endpoint_name = "get_brands"
    url = f"{BASE_URL}/validation-scripts/by-endpoint-name/{endpoint_name}"

    # First check if scripts exist
    check_url = f"{BASE_URL}/validation-scripts/by-endpoint-name/{endpoint_name}"
    check_response = requests.get(check_url)
    print(f"Scripts before deletion: {check_response.status_code}")
    if check_response.status_code == 200:
        scripts_data = check_response.json()
        print(f"Found {scripts_data.get('total', 0)} scripts")

    # Delete scripts
    response = requests.delete(url)

    print(f"Delete Status Code: {response.status_code}")
    if response.status_code == 204:
        print("✅ Validation scripts deletion successful!")
    else:
        print(f"❌ Validation scripts deletion failed: {response.text}")

    # Verify deletion
    verify_response = requests.get(check_url)
    print(f"Scripts after deletion: {verify_response.status_code}")
    if verify_response.status_code == 200:
        scripts_data = verify_response.json()
        print(f"Remaining scripts: {scripts_data.get('total', 0)}")

    return response


def test_delete_constraints():
    """Test deleting constraints by endpoint name."""
    print("\n=== Testing DELETE /constraints/by-endpoint-name/get_brands ===")
    endpoint_name = "get_brands"
    url = f"{BASE_URL}/constraints/by-endpoint-name/{endpoint_name}"

    # First check if constraints exist
    check_url = f"{BASE_URL}/constraints/by-endpoint-name/{endpoint_name}"
    check_response = requests.get(check_url)
    print(f"Constraints before deletion: {check_response.status_code}")
    if check_response.status_code == 200:
        constraints_data = check_response.json()
        print(f"Found {constraints_data.get('total', 0)} constraints")

    # Delete constraints
    response = requests.delete(url)

    print(f"Delete Status Code: {response.status_code}")
    if response.status_code == 204:
        print("✅ Constraints deletion successful!")
    else:
        print(f"❌ Constraints deletion failed: {response.text}")

    # Verify deletion
    verify_response = requests.get(check_url)
    print(f"Constraints after deletion: {verify_response.status_code}")
    if verify_response.status_code == 200:
        constraints_data = verify_response.json()
        print(f"Remaining constraints: {constraints_data.get('total', 0)}")

    return response


def test_workflow():
    """Test complete workflow: export -> delete scripts -> delete constraints."""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE WORKFLOW")
    print("=" * 60)

    endpoint_name = "get_brands"

    # Step 1: Export scripts to Python file
    print("\n🔸 Step 1: Export validation scripts to Python file")
    export_response = test_export_scripts_to_python()

    if export_response.status_code != 200:
        print("❌ Export failed, stopping workflow")
        return

    # Step 2: Delete validation scripts
    print("\n🔸 Step 2: Delete validation scripts")
    delete_scripts_response = test_delete_validation_scripts()

    if delete_scripts_response.status_code != 204:
        print("❌ Script deletion failed, stopping workflow")
        return

    # Step 3: Delete constraints
    print("\n🔸 Step 3: Delete constraints")
    delete_constraints_response = test_delete_constraints()

    if delete_constraints_response.status_code == 204:
        print("\n✅ Complete workflow successful!")
    else:
        print("\n❌ Constraint deletion failed")


def main():
    """Run all tests."""
    print("Testing New Endpoints")
    print("=" * 50)

    try:
        # Test individual endpoints
        test_export_scripts_to_python()
        test_delete_validation_scripts()
        test_delete_constraints()

        # Test complete workflow
        test_workflow()

        print("\n" + "=" * 50)
        print("All tests completed!")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection error: Make sure the server is running on http://localhost:8000"
        )
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
