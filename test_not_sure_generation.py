#!/usr/bin/env python3
"""
Test script to verify %not-sure% generation for Bill endpoints
"""
import os
import sys
import json

# Setup path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import modules
from kat.data_generator.path_param_analyzer import PathParameterAnalyzer

def test_path_param_analyzer():
    """Test the path parameter analyzer with Bill API"""
    print("=" * 60)
    print("Testing Path Parameter Analyzer")
    print("=" * 60)
    
    # Load Bill OpenAPI spec
    with open('Dataset/Bill/openapi.json', 'r') as f:
        swagger_spec = json.load(f)
    
    analyzer = PathParameterAnalyzer(swagger_spec)
    
    # Test endpoints
    endpoints = [
        'get-/api/v1/Bills/{billId}',
        'get-/api/v1/Bills/{billId}/NewsArticles',
        'get-/api/v1/Bills/{billId}/Stages/{billStageId}',
        'get-/api/v1/Bills/{billId}/Stages/{billStageId}/Amendments/{amendmentId}',
        'get-/api/v1/Bills/{billId}/Stages/{billStageId}/PingPongItems/{pingPongItemId}'
    ]
    
    print("Path Parameter Analysis:")
    for endpoint in endpoints:
        print(f"\n{endpoint}:")
        analysis = analyzer.analyze_path_parameters(endpoint)
        for param, certainty in analysis.items():
            print(f"  {param}: {certainty}")
            if certainty == 'uncertain':
                deps = analyzer.get_dependency_endpoints(param, endpoint)
                print(f"    Dependencies: {deps}")
    
    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)

def test_data_generator():
    """Test the data generator with updated analyzer"""
    print("=" * 60)
    print("Testing Data Generator with %not-sure%")
    print("=" * 60)
    
    try:
        from kat.test_case_generator.test_case_generator import TestCaseGenerator
        
        # Initialize generator
        generator = TestCaseGenerator(
            service_name="Bill",
            collection="Default",
            save_prompts=True,
            regenerate_test_data=True,  # Force regeneration
            data_generation_mode="2xx",  # Only 2xx to see %not-sure%
            clear_test_cases=False,
        )
        
        # Generate test data for endpoint with uncertain path params
        endpoint = "get-/api/v1/Bills/{billId}/NewsArticles"
        print(f"Generating test data for: {endpoint}")
        
        generator.generate_test_data_for(endpoint)
        
        # Check result
        csv_file = "KAT_CLONE_TEST_CASES/Bill/TestData/csv/_api_v1_Bills_billId_NewsArticles_GetNewsArticles_param.csv"
        if os.path.exists(csv_file):
            print(f"Generated CSV: {csv_file}")
            with open(csv_file, 'r') as f:
                content = f.read()
                if '%not-sure%' in content:
                    print("✅ SUCCESS: Found %not-sure% markers in generated data!")
                    print("Sample lines with %not-sure%:")
                    for i, line in enumerate(content.split('\n')):
                        if '%not-sure%' in line:
                            print(f"  Line {i+1}: {line}")
                else:
                    print("❌ WARNING: No %not-sure% markers found in generated data")
        else:
            print("❌ ERROR: CSV file not generated")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_path_param_analyzer()
    print("\n")
    test_data_generator()
