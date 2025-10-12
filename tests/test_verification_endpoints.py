"""
Test script for verification endpoints.
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Test data for get_brands endpoint
test_data_request = {
    "test_data_items": [
        {
            "request_params": {"general": "electronics"},
            "request_headers": {"Content-Type": "application/json"},
            "request_body": None,
            "expected_status_code": 200,
        },
        {
            "request_params": {"general": "clothing"},
            "request_headers": {"Content-Type": "application/json"},
            "request_body": None,
            "expected_status_code": 200,
        },
    ],
    "timeout": 30,
}

# Mock request-response pair for get_brands endpoint
request_response_request = {
    "request_response_pairs": [
        {
            "request": {
                "method": "GET",
                "url": "http://localhost:3000/brands?general=electronics",
                "headers": {"Content-Type": "application/json"},
                "params": {"general": "electronics"},
                "body": None,
            },
            "response": {
                "status_code": 201,
                "headers": {"Content-Type": "application/json"},
                "body": [
                    {
                        "id": "1",
                        "name": "Samsung",
                        "slug": "samsung",
                        "description": "Leading electronics brand",
                    },
                    {
                        "id": "2",
                        "name": "Apple",
                        "slug": "apple",
                        "description": "Innovative technology brand",
                    },
                ],
            },
        },
        {
            "request": {
                "method": "GET",
                "url": "http://localhost:3000/brands?general=clothing",
                "headers": {"Content-Type": "application/json"},
                "params": {"general": "clothing"},
                "body": None,
            },
            "response": {
                "status_code": 201,
                "headers": {"Content-Type": "application/json"},
                "body": [
                    {
                        # "id": "3",
                        "name": "Nike",
                        "slug": "nike",
                        "description": "Athletic wear brand",
                    },
                    {
                        # "id": "4",
                        "name": "Adidas",
                        "slug": "adidas",
                        "description": "Sports brand",
                    },
                ],
            },
        },
    ],
    "timeout": 30,
}


def test_verify_test_data():
    """Test the verify test data endpoint."""
    print("Testing POST /verify/test-data/by-endpoint-name/get_brands")

    response = requests.post(
        f"{BASE_URL}/verify/test-data/by-endpoint-name/get_brands",
        json=test_data_request,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        print("Test data verification successful!")
    else:
        print("Test data verification failed!")

    return response


def test_verify_request_response():
    """Test the verify request-response endpoint."""
    print("\nTesting POST /verify/request-response/get_brands")

    response = requests.post(
        f"{BASE_URL}/verify/request-response/get_brands",
        json=request_response_request,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        print("Request-response verification successful!")
    else:
        print("Request-response verification failed!")

    return response


def main():
    """Run all tests."""
    print("Testing Verification Endpoints")
    print("=" * 50)

    try:
        # Test verify test data endpoint
        test_verify_test_data()

        # Test verify request-response endpoint
        test_verify_request_response()

        print("\nAll tests completed!")

    except requests.exceptions.ConnectionError:
        print(
            "Connection error: Make sure the server is running on http://localhost:8000"
        )
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
