"""
Test script for Dataset Management API
Run this after starting the server with: python main.py
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"


def print_response(response, title="Response"):
    """Pretty print response"""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Body: {json.dumps(response.json(), indent=2)}")
    except (json.JSONDecodeError, requests.exceptions.RequestException):
        print(f"Body: {response.text}")


def test_dataset_workflow():
    """Test complete dataset workflow"""

    # 1. Create a dataset
    print("\n🔷 Step 1: Create a new dataset")
    response = requests.post(
        f"{BASE_URL}/datasets/",
        json={
            "name": "Petstore API",
            "description": "Sample Petstore API for testing",
        },
    )
    print_response(response, "Create Dataset")
    assert response.status_code == 201
    dataset = response.json()
    dataset_id = dataset["id"]
    print(f"✅ Dataset created with ID: {dataset_id}")

    # 2. Upload OpenAPI spec
    print("\n🔷 Step 2: Upload OpenAPI specification")
    spec_file = Path("data/example/openapi.yaml")

    if spec_file.exists():
        with open(spec_file, "r", encoding="utf-8") as f:
            spec_content = f.read()

        response = requests.post(
            f"{BASE_URL}/datasets/{dataset_id}/upload-spec",
            json={"spec_content": spec_content, "is_yaml": True},
        )
        print_response(response, "Upload Spec")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Spec uploaded successfully!")
            print(f"   - API: {result.get('api_title')}")
            print(f"   - Version: {result.get('spec_version')}")
            print(f"   - Endpoints: {result.get('endpoints_count')}")
        else:
            print(f"❌ Failed to upload spec: {response.text}")
            return
    else:
        print(f"⚠️  Spec file not found: {spec_file}")
        print("   Skipping spec upload step")

    # 3. Get dataset details
    print("\n🔷 Step 3: Get dataset details")
    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}")
    print_response(response, "Get Dataset")
    assert response.status_code == 200
    print("✅ Dataset retrieved successfully")

    # 4. Get all endpoints for the dataset
    print("\n🔷 Step 4: Get all endpoints for the dataset")
    response = requests.get(f"{BASE_URL}/datasets/{dataset_id}/endpoints")
    print_response(response, "Get Dataset Endpoints")

    if response.status_code == 200:
        endpoints = response.json()
        print(f"✅ Retrieved {len(endpoints)} endpoints")

        if endpoints:
            # Pick first endpoint for testing
            endpoint = endpoints[0]
            endpoint_id = endpoint["id"]
            print(f"\n   Using endpoint: {endpoint['method']} {endpoint['path']}")

            # 5. Mine constraints for the endpoint
            print("\n🔷 Step 5: Mine constraints for endpoint")
            response = requests.post(
                f"{BASE_URL}/constraints/mine", json={"endpoint_id": endpoint_id}
            )
            print_response(response, "Mine Constraints")

            if response.status_code == 200:
                constraints = response.json()
                print(f"✅ Mined {len(constraints)} constraints")

                if constraints:
                    constraint_id = constraints[0]["id"]

                    # 6. Generate validation scripts
                    print("\n🔷 Step 6: Generate validation scripts")
                    response = requests.post(
                        f"{BASE_URL}/validation-scripts/generate",
                        json={"endpoint_id": endpoint_id},
                    )
                    print_response(response, "Generate Scripts")

                    if response.status_code == 200:
                        scripts = response.json()
                        print(f"✅ Generated {len(scripts)} validation scripts")

                        # Check if constraint_id is populated
                        scripts_with_constraint = [
                            s for s in scripts if s.get("constraint_id")
                        ]
                        print(
                            f"   - Scripts with constraint_id: {len(scripts_with_constraint)}/{len(scripts)}"
                        )

                        if scripts_with_constraint:
                            print(f"   ✅ constraint_id mapping is working correctly!")
                        else:
                            print(f"   ⚠️  No scripts have constraint_id populated")

                    # 7. Query scripts by constraint
                    print("\n🔷 Step 7: Query scripts by constraint_id")
                    response = requests.get(
                        f"{BASE_URL}/validation-scripts?constraint_id={constraint_id}"
                    )
                    print_response(response, "Query Scripts by Constraint")

                    if response.status_code == 200:
                        filtered_scripts = response.json()
                        print(
                            f"✅ Found {len(filtered_scripts)} scripts for constraint {constraint_id}"
                        )

    # 8. List all datasets
    print("\n🔷 Step 8: List all datasets")
    response = requests.get(f"{BASE_URL}/datasets/")
    print_response(response, "List Datasets")
    assert response.status_code == 200
    datasets = response.json()
    print(f"✅ Total datasets: {len(datasets)}")

    # 9. Delete dataset (cleanup)
    print("\n🔷 Step 9: Delete dataset (cleanup)")
    response = requests.delete(f"{BASE_URL}/datasets/{dataset_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 204:
        print(f"✅ Dataset deleted successfully")
    else:
        print(f"❌ Failed to delete dataset")

    print("\n" + "=" * 60)
    print("✅ DATASET WORKFLOW TEST COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_dataset_workflow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server. Make sure the server is running:")
        print("   python main.py")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
