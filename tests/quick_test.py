#!/usr/bin/env python3
import os
import sys
import json

# Setup path
sys.path.append('src')

# Import modules
from kat.data_generator.path_param_analyzer import PathParameterAnalyzer

# Load Bill OpenAPI spec
with open('Dataset/Bill/openapi.json', 'r') as f:
    swagger_spec = json.load(f)

analyzer = PathParameterAnalyzer(swagger_spec)

# Test a simple endpoint
endpoint = 'get-/api/v1/Bills/{billId}/NewsArticles'
analysis = analyzer.analyze_path_parameters(endpoint)

print(f"Endpoint: {endpoint}")
print(f"Analysis: {analysis}")

# Check if billId is uncertain
billId_certainty = analysis.get('billId', 'unknown')
print(f"billId certainty: {billId_certainty}")

if billId_certainty == 'uncertain':
    dependencies = analyzer.get_dependency_endpoints('billId', endpoint)
    print(f"Dependencies for billId: {dependencies}")
    
print("\nShould use %not-sure%:", analyzer.should_use_not_sure_marker('billId', endpoint, '2xx'))
