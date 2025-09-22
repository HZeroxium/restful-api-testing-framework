#!/usr/bin/env python3
"""
Test runner to verify %not-sure% generation
"""
import os
import sys

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test path parameter analyzer first
print("=" * 60)
print("Testing Path Parameter Analyzer")
print("=" * 60)

from kat.data_generator.path_param_analyzer import PathParameterAnalyzer
import json

# Load swagger spec
with open('Dataset/Bill/openapi.json', 'r') as f:
    swagger_spec = json.load(f)

analyzer = PathParameterAnalyzer(swagger_spec)

# Test endpoint
endpoint = 'get-/api/v1/Bills/{billId}/NewsArticles'
analysis = analyzer.analyze_path_parameters(endpoint)

print(f"Endpoint: {endpoint}")
print(f"Analysis: {analysis}")

for param, certainty in analysis.items():
    print(f"  {param}: {certainty}")
    if certainty == 'uncertain':
        deps = analyzer.get_dependency_endpoints(param, endpoint)
        print(f"    Dependencies: {deps}")

# Test %not-sure% marker
should_use_marker = analyzer.should_use_not_sure_marker('billId', endpoint, '2xx')
print(f"\nShould use %not-sure% for billId in 2xx case: {should_use_marker}")

print("\n" + "=" * 60)
print("Path Parameter Analysis Complete")
print("=" * 60)

# Test if data generator will use this properly
print("\nNow testing integration with data generator...")

try:
    from kat.test_case_generator.test_case_generator import TestCaseGenerator
    
    print("Creating TestCaseGenerator...")
    generator = TestCaseGenerator(
        service_name="Bill",
        collection="Default",
        save_prompts=True,
        regenerate_test_data=True,
        data_generation_mode="2xx",  # Only 2xx to see %not-sure%
        clear_test_cases=False,
    )
    
    print(f"Generating test data for: {endpoint}")
    generator.generate_test_data_for(endpoint)
    
    # Check the output
    csv_file = "KAT_CLONE_TEST_CASES/Bill/TestData/csv/_api_v1_Bills_billId_NewsArticles_GetNewsArticles_param.csv"
    
    if os.path.exists(csv_file):
        print(f"\n✅ Generated CSV file: {csv_file}")
        
        with open(csv_file, 'r') as f:
            content = f.read()
            
        print("\nFirst 10 lines of generated CSV:")
        lines = content.split('\n')
        for i, line in enumerate(lines[:10]):
            if line.strip():
                print(f"  {i+1}: {line}")
        
        # Check for %not-sure% markers
        if '%not-sure%' in content:
            print("\n🎉 SUCCESS: Found %not-sure% markers!")
            print("\nLines containing %not-sure%:")
            for i, line in enumerate(lines):
                if '%not-sure%' in line:
                    print(f"  Line {i+1}: {line}")
        else:
            print("\n⚠️  WARNING: No %not-sure% markers found")
            print("This could mean:")
            print("  1. The analyzer is not classifying billId as uncertain")
            print("  2. The prompt is not being updated correctly")
            print("  3. The LLM is not following the %not-sure% instruction")
            
    else:
        print(f"\n❌ ERROR: CSV file not found at {csv_file}")
        
except Exception as e:
    print(f"\n❌ ERROR in data generation: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
