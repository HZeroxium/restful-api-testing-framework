"""
Test to verify that path parameters are not added to query string.
This reproduces the issue from the Canada Holidays API test case.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from sequence_runner.data_merge import merge_test_data

def test_path_param_not_in_query():
    """Test that holidayId (path param) is NOT added to query params"""
    
    # Setup: endpoint with path parameter {holidayId}
    endpoint = "get-/api/v1/holidays/{holidayId}"
    
    # Base params and body (empty initially)
    base_params = {}
    base_body = {}
    
    # Path variables defined in the spec
    path_vars = {"holidayId": None}  # Will be filled from CSV
    
    # CSV test data row that includes both query params AND path param
    test_data_row = {
        "year": 2025,
        "holidayId": 1,  # This is a PATH param, NOT a query param!
        "expected_status_code": "2xx",
        "reason": "llm_success_ignore_optional"
    }
    
    # Merge test data
    merged_params, merged_body, csv_path_vars, not_sure_params = merge_test_data(
        base_params=base_params,
        base_body=base_body,
        test_data_row=test_data_row,
        endpoint=endpoint,
        path_vars=path_vars,
        data_for="params"
    )
    
    print("=" * 60)
    print("TEST: Path parameter should NOT appear in query params")
    print("=" * 60)
    print(f"\nEndpoint: {endpoint}")
    print(f"Test data: {test_data_row}")
    print(f"\nResults:")
    print(f"  - merged_params (query): {merged_params}")
    print(f"  - csv_path_vars (path): {csv_path_vars}")
    print(f"  - merged_body: {merged_body}")
    
    # Assertions
    assert "holidayId" not in merged_params, \
        f"❌ FAIL: holidayId should NOT be in query params! Got: {merged_params}"
    
    assert "holidayId" in csv_path_vars, \
        f"❌ FAIL: holidayId should be in csv_path_vars! Got: {csv_path_vars}"
    
    assert csv_path_vars["holidayId"] == 1, \
        f"❌ FAIL: holidayId value should be 1! Got: {csv_path_vars['holidayId']}"
    
    assert "year" in merged_params, \
        f"❌ FAIL: year should be in query params! Got: {merged_params}"
    
    assert merged_params["year"] == 2025, \
        f"❌ FAIL: year value should be 2025! Got: {merged_params['year']}"
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print(f"  ✓ holidayId correctly extracted as path variable")
    print(f"  ✓ holidayId NOT added to query parameters")
    print(f"  ✓ year correctly added to query parameters")
    print("\nExpected URL format:")
    print(f"  https://canada-holidays.ca/api/v1/holidays/1?year=2025")
    print(f"\nNOT (incorrect):")
    print(f"  https://canada-holidays.ca/api/v1/holidays/1?year=2025&holidayId=1")
    print("=" * 60)

if __name__ == "__main__":
    test_path_param_not_in_query()
