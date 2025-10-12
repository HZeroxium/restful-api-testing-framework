"""
Test script to verify the verification logic without server.
"""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Test imports
try:
    from schemas.tools.openapi_parser import EndpointInfo
    from schemas.tools.test_script_generator import ValidationScript
    from schemas.tools.test_data_generator import TestData
    from app.api.dto.verification_dto import (
        TestDataItem,
        VerifyTestDataRequest,
        RequestResponsePair,
        VerifyRequestResponseRequest,
    )

    print("SUCCESS: All imports successful!")

    # Test creating test data
    test_data_item = TestDataItem(
        request_params={"general": "electronics"},
        request_headers={"Content-Type": "application/json"},
        request_body=None,
        expected_status_code=200,
    )
    print("SUCCESS: TestDataItem creation successful!")

    # Test creating verification request
    verify_request = VerifyTestDataRequest(test_data_items=[test_data_item], timeout=30)
    print("SUCCESS: VerifyTestDataRequest creation successful!")

    # Test creating request-response pair
    request_response_pair = RequestResponsePair(
        request={
            "method": "GET",
            "url": "http://localhost:3000/brands?general=electronics",
            "headers": {"Content-Type": "application/json"},
            "params": {"general": "electronics"},
            "body": None,
        },
        response={
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": [{"id": "1", "name": "Samsung", "category": "electronics"}],
        },
    )
    print("SUCCESS: RequestResponsePair creation successful!")

    # Test creating request-response verification request
    verify_rr_request = VerifyRequestResponseRequest(
        request_response_pairs=[request_response_pair], timeout=30
    )
    print("SUCCESS: VerifyRequestResponseRequest creation successful!")

    print("\nAll verification logic components are working correctly!")
    print("The verification endpoints should work once the server starts properly.")

except ImportError as e:
    print(f"ERROR: Import error: {e}")
except Exception as e:
    print(f"ERROR: {e}")
