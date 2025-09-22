import sys
import os
sys.path.insert(0, 'src')

# Test imports first
try:
    from kat.data_generator.path_param_analyzer import PathParameterAnalyzer
    print("✅ PathParameterAnalyzer imported successfully")
except Exception as e:
    print(f"❌ Failed to import PathParameterAnalyzer: {e}")
    exit(1)

try:
    import json
    with open('Dataset/Bill/openapi.json', 'r') as f:
        swagger_spec = json.load(f)
    print("✅ OpenAPI spec loaded successfully")
except Exception as e:
    print(f"❌ Failed to load OpenAPI spec: {e}")
    exit(1)

# Test analyzer
try:
    analyzer = PathParameterAnalyzer(swagger_spec)
    print("✅ PathParameterAnalyzer created successfully")
except Exception as e:
    print(f"❌ Failed to create PathParameterAnalyzer: {e}")
    exit(1)

# Test simple analysis
try:
    endpoint = 'get-/api/v1/Bills/{billId}/NewsArticles'
    analysis = analyzer.analyze_path_parameters(endpoint)
    print(f"✅ Analysis result: {analysis}")
    
    billId_certainty = analysis.get('billId')
    print(f"billId certainty: {billId_certainty}")
    
    if billId_certainty == 'uncertain':
        print("✅ billId correctly identified as uncertain")
        should_use = analyzer.should_use_not_sure_marker('billId', endpoint, '2xx')
        print(f"Should use %not-sure% marker: {should_use}")
    else:
        print(f"⚠️  billId identified as: {billId_certainty}")
        
except Exception as e:
    print(f"❌ Failed analysis: {e}")
    import traceback
    traceback.print_exc()

print("Basic test complete")
