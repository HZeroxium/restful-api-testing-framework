#!/usr/bin/env python3
import os
import sys
import json

# Setup path
sys.path.append('src')

# Load Bill OpenAPI spec
with open('Dataset/Bill/openapi.json', 'r') as f:
    swagger_spec = json.load(f)

# Debug analyzer logic step by step
endpoint = 'get-/api/v1/Bills/{billId}/NewsArticles'
param_name = 'billId'

print(f"=== Debug Analysis for {param_name} in {endpoint} ===")

# Check constraints
method = endpoint.split('-')[0]
path = '-'.join(endpoint.split('-')[1:])
print(f"Method: {method}, Path: {path}")

endpoint_spec = swagger_spec.get('paths', {}).get(path, {}).get(method.lower(), {})
parameters = endpoint_spec.get('parameters', [])

billId_param = None
for param in parameters:
    if param.get('name') == param_name:
        billId_param = param
        break

if billId_param:
    print(f"Found parameter: {json.dumps(billId_param, indent=2)}")
    schema = billId_param.get('schema', {})
    
    # Check constraints
    print("\n--- Constraint Analysis ---")
    print(f"Has enum: {'enum' in schema}")
    print(f"Has format: {schema.get('format', 'None')}")
    print(f"Has pattern: {'pattern' in schema}")
    print(f"Has minimum: {'minimum' in schema} (value: {schema.get('minimum', 'None')})")
    print(f"Has maximum: {'maximum' in schema} (value: {schema.get('maximum', 'None')})")
    
    # Range analysis
    if 'minimum' in schema and 'maximum' in schema:
        min_val = schema['minimum']
        max_val = schema['maximum']
        range_size = max_val - min_val
        print(f"Range size: {range_size}")
        print(f"Small range (<=100): {range_size <= 100}")
    
    # Description analysis
    description = billId_param.get('description', '')
    print(f"\nDescription: '{description}'")
    
    # Check if has helpful description
    helpful_patterns = [
        'valid values are',
        'must be one of',
        'format:',
        'example:',
        'yyyy-mm-dd',
        'iso 8601',
    ]
    
    has_helpful_desc = any(pattern in description.lower() for pattern in helpful_patterns)
    print(f"Has helpful description: {has_helpful_desc}")
    
    # Standard pattern check
    date_time_patterns = ['year', 'month', 'day', 'date', 'time']
    has_standard_pattern = any(pattern in param_name.lower() for pattern in date_time_patterns)
    print(f"Has standard pattern: {has_standard_pattern}")
    
    # Overall determination
    has_clear_constraints = ('enum' in schema or 
                           schema.get('format') in ['date', 'date-time', 'email', 'uuid'] or
                           'pattern' in schema or
                           ('minimum' in schema and 'maximum' in schema and 
                            schema['maximum'] - schema['minimum'] <= 100))
    
    print(f"\n--- Final Analysis ---")
    print(f"Has clear constraints: {has_clear_constraints}")
    print(f"Has helpful description: {has_helpful_desc}")
    print(f"Has standard pattern: {has_standard_pattern}")
    
    if has_clear_constraints or has_helpful_desc or has_standard_pattern:
        certainty = 'certain'
    else:
        certainty = 'uncertain'
    
    print(f"Final certainty: {certainty}")
    
else:
    print(f"Parameter {param_name} not found!")
