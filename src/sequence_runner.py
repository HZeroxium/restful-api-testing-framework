#!/usr/bin/env python3
"""
Sequence Runner - Execute API test sequences with test data mapping
Usage: python -m src.test_case_generator.sequence_runner --service "Canada Holidays" [--endpoint endpoint_name]
"""

import os
import json
import requests
import csv
import time
import argparse
import logging
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from typing import Dict, List, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
test_case_dir_name = "KAT_CLONE_TEST_CASES" 
class SequenceRunner:
    def __init__(self, service_name: str, base_url: str = "http://localhost:8000", auth_token: str = None, endpoint: List[str] = None, skip_preload: bool = False):
        self.service_name = service_name
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint

        # Setup paths
        self.base_dir = Path(__file__).resolve().parent.parent / test_case_dir_name / service_name
        self.test_case_dir = self.base_dir / "test_case_generator"
        self.test_data_dir = self.base_dir / "TestData/csv"
        self.topolist_path = self.base_dir / "ODG/topolist.json"
        self.output_csv_dir = self.base_dir / "Result"
        # Setup output directory for response logs
        self.output_dir = Path(__file__).resolve().parent / "Output" / service_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default headers
        self.session.headers.update({
            'User-Agent': 'API-Test-Runner/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Cache for responses
        self.response_cache = {}
        
        # Global cache for dependency responses (không reset mỗi test case)
        self.global_dependency_cache = {}
        
        # Cache available IDs for random selection
        self.available_ids_cache = {
            'holidayId': [],
            'provinceId': []
        }
        
        # Authentication token storage
        self.auth_token = auth_token
        
        # CSV writer setup
        self.csv_file = None
        self.csv_writer = None

        self.setup_csv_output()
    
    def setup_csv_output(self):
        # Đảm bảo thư mục Result tồn tại
        os.makedirs(self.output_csv_dir, exist_ok=True)

        csv_path = self.output_csv_dir / f"test_results_{self.service_name.replace(' ', '_')}.csv"

        self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        fieldnames = [
            'test_case_id', 'step_number', 'endpoint', 'method',
            'test_data_row', 'request_params', 'request_body', 'final_url',
            'response_status', 'expected_status', 'execution_time', 'status'
        ]
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        logger.info(f"CSV output will be saved to: {csv_path}")

    
    def load_topolist(self) -> List[str]:
        """Load endpoint sequence from topolist.json"""
        if not self.topolist_path.exists():
            logger.warning(f"Topolist not found: {self.topolist_path}")
            return []
        
        with open(self.topolist_path, 'r') as f:
            topolist = json.load(f)
        
        logger.info(f"Loaded {len(topolist)} endpoints from topolist")
        return topolist
    
    def find_test_case_files(self, endpoint_name: Optional[str] = None) -> List[Path]:
        """Find test case JSON files for given endpoint or all if None"""
        if not self.test_case_dir.exists():
            logger.error(f"Test case directory not found: {self.test_case_dir}")
            return []
        
        json_files = list(self.test_case_dir.glob("*.json"))
        
        if endpoint_name:
            # Filter for specific endpoint
            filtered_files = [f for f in json_files if endpoint_name in f.name]
            logger.info(f"Found {len(filtered_files)} test case files for endpoint: {endpoint_name}")
        else:
            filtered_files = [f for f in json_files if not f.name.startswith('simplified_swagger')]
            logger.info(f"Found {len(filtered_files)} test case files total")
        
        return sorted(filtered_files)
    
    def find_test_data_files(self, endpoint_identifier: str):
        candidates = {
            "param": [
                f"{endpoint_identifier}_param.csv",
                f"_{endpoint_identifier}_param.csv",
            ],
            "body": [
                f"{endpoint_identifier}_body.csv",
                f"_{endpoint_identifier}_body.csv",
            ],
            "any": [
                f"{endpoint_identifier}.csv",
                f"_{endpoint_identifier}.csv",
            ]
        }
        found = {"param": None, "body": None}
        for kind, patterns in candidates.items():
            for p in patterns:
                fpath = self.test_data_dir / p
                if fpath.exists():
                    if kind == "any":
                        # fallback: coi như param
                        found["param"] = fpath
                    else:
                        found[kind] = fpath
                    break
        return found

    
    def load_test_data(self, csv_file: Path) -> List[Dict[str, Any]]:
        """Load test data from CSV file"""
        if csv_file is None:
            return []
            
        test_data = []
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                test_data = list(reader)
            logger.debug(f"Loaded {len(test_data)} rows from {csv_file.name}")
        except Exception as e:
            logger.error(f"Error loading test data from {csv_file}: {e}")
        
        return test_data
    
    def resolve_dependencies(self, params: Dict, body: Dict, data_dependencies: Dict, current_step: int, step_responses: List[Dict]) -> tuple:
        """Resolve data dependencies using global cache và random ID selection"""
        import random
        
        resolved_params = params.copy()
        resolved_body = body.copy()
        
        for dep_key, dep_info in data_dependencies.items():
            if isinstance(dep_info, dict) and 'from_step' in dep_info:
                from_step = dep_info['from_step']
                field_mappings = dep_info.get('field_mappings', {})
                
                # Use global cache instead of step cache
                prev_response = None
                
                # Try to find cached data for this dependency key
                for cache_key, cached_data in self.global_dependency_cache.items():
                    # Check if this cache might contain data for our dependency
                    if any(keyword in cache_key.lower() for keyword in dep_key.lower().split('_')):
                        prev_response = cached_data
                        logger.info(f"  📋 Using global cached {cache_key} data for {dep_key}")
                        break
                
                # Fallback: try to match by dependency endpoint from test case
                if not prev_response:
                    from_step_idx = from_step - 1
                    if 0 <= from_step_idx < len(step_responses) and step_responses[from_step_idx]:
                        prev_response = step_responses[from_step_idx]
                        logger.info(f"  📋 Using step response for {dep_key}")
                
                # Another fallback: try any cached data
                if not prev_response and self.global_dependency_cache:
                    cache_key = list(self.global_dependency_cache.keys())[0]
                    prev_response = self.global_dependency_cache[cache_key]
                    logger.info(f"  📋 Using fallback cached {cache_key} data for {dep_key}")
                
                if prev_response:
                    
                    # Handle field mappings with random selection
                    if field_mappings:
                        for target_field, source_field in field_mappings.items():
                            resolved_value = None
                            
                            # Use available IDs cache for random selection
                            if target_field in self.available_ids_cache and self.available_ids_cache[target_field]:
                                resolved_value = random.choice(self.available_ids_cache[target_field])
                                logger.info(f"🎲 Random selected {target_field} = {resolved_value} from {len(self.available_ids_cache[target_field])} available IDs")
                            else:
                                # Fallback to original extraction logic
                                if target_field == 'provinceId' and source_field == 'provinces':
                                    provinces = self.extract_from_response(prev_response, source_field)
                                    if isinstance(provinces, list) and len(provinces) > 0:
                                        resolved_value = provinces[0].get('id') if isinstance(provinces[0], dict) else None
                                else:
                                    resolved_value = self.extract_from_response(prev_response, source_field)
                                    
                                    if resolved_value is None:
                                        for key, value in prev_response.items():
                                            if isinstance(value, list) and len(value) > 0:
                                                resolved_value = self.extract_from_response(value[0], source_field)
                                                if resolved_value is not None:
                                                    break
                            
                            if resolved_value is not None:
                                resolved_params[target_field] = resolved_value
                                logger.info(f"✅ Resolved dependency: {target_field} = {resolved_value}")
                            else:
                                logger.warning(f"❌ Failed to resolve dependency: {target_field} from {source_field}")
                    else:
                        # Fallback: use dep_key directly
                        if dep_key in self.available_ids_cache and self.available_ids_cache[dep_key]:
                            resolved_value = random.choice(self.available_ids_cache[dep_key])
                            resolved_params[dep_key] = resolved_value
                            logger.info(f"🎲 Random selected {dep_key} = {resolved_value}")
                        else:
                            resolved_value = self.extract_from_response(prev_response, dep_key)
                            if resolved_value is not None:
                                resolved_params[dep_key] = resolved_value
                                logger.info(f"✅ Resolved dependency: {dep_key} = {resolved_value}")
                else:
                    logger.warning(f"❌ No cached data available for dependency resolution")
        
        return resolved_params, resolved_body
    
    def extract_from_response(self, response_data: Dict, path: str) -> Any:
        """Extract value from response using JSONPath-like syntax"""
        if not path:
            return response_data
        
        current = response_data
        
        # Handle array access - get first item if it's an array and we need a specific field
        if isinstance(current, list) and len(current) > 0:
            current = current[0]  # Take first item from array
        
        # Navigate path
        for key in path.split('.'):
            if key == '':
                continue
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                current = current[int(key)]
            elif isinstance(current, list) and len(current) > 0:
                # If it's an array and key is not numeric, try to get from first item
                current = current[0]
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            else:
                return None
        
        return current
    
    def extract_expected_status(self, test_data_row: Dict) -> str:
        """Extract expected status code from test data"""
        if test_data_row is None:
            return '2xx'
            
        # Check for expected status in different possible fields at root level
        for field in ['expected_status_code', 'expected_code']:
            if field in test_data_row and test_data_row[field]:
                return test_data_row[field]
        
        # Check nested structure: {"param": {...}, "body": {...}}
        if "param" in test_data_row and isinstance(test_data_row["param"], dict):
            param_data = test_data_row["param"]
            for field in ['expected_status_code', 'expected_code']:
                if field in param_data and param_data[field]:
                    return param_data[field]
                    
            # Try to extract from data field if it's JSON in param section
            if 'data' in param_data and isinstance(param_data['data'], str):
                try:
                    data_obj = json.loads(param_data['data'])
                    if isinstance(data_obj, dict):
                        return data_obj.get('expected_code', data_obj.get('expected_status_code', '2xx'))
                except json.JSONDecodeError:
                    pass
        
        # Try to extract from data field if it's JSON at root level
        if 'data' in test_data_row and isinstance(test_data_row['data'], str):
            try:
                data_obj = json.loads(test_data_row['data'])
                if isinstance(data_obj, dict):
                    return data_obj.get('expected_code', data_obj.get('expected_status_code', '2xx'))
            except json.JSONDecodeError:
                pass
        
        return '2xx'  # Default expectation
    
    def is_status_match(self, actual_status: int, expected_pattern: str) -> bool:
        """Check if actual status matches expected pattern"""
        if not expected_pattern:
            return True
            
        expected_pattern = str(expected_pattern).lower()
        
        # Handle patterns like 2xx, 3xx, 4xx, 5xx
        if expected_pattern.endswith('xx') and len(expected_pattern) == 3:
            expected_class = expected_pattern[0]
            actual_class = str(actual_status)[0]
            return expected_class == actual_class
        
        # Handle exact status codes like 200, 404, etc.
        if expected_pattern.isdigit():
            return actual_status == int(expected_pattern)
        
        # Handle ranges like 200-299
        if '-' in expected_pattern:
            try:
                start, end = expected_pattern.split('-')
                return int(start) <= actual_status <= int(end)
            except ValueError:
                pass
        # Default: assume 2xx if we can't parse
        return 200 <= actual_status < 300

    def resolve_not_sure_parameter(self, param_name: str, endpoint: str, step_responses: List[Dict] = None) -> Optional[str]:
        """
        Resolve %not-sure% parameter by extracting value from previous step responses
        """
        logger.info(f"🔍 Resolving %not-sure% parameter: {param_name} for endpoint: {endpoint}")
        
        # Try to get from cache first
        if param_name in self.available_ids_cache and self.available_ids_cache[param_name]:
            value = self.available_ids_cache[param_name][0]
            logger.info(f"  ✅ Found cached value for {param_name}: {value}")
            return value
        
        # Try to extract from previous step responses
        if step_responses:
            logger.info(f"  🔍 Looking for {param_name} in {len(step_responses)} previous step responses")
            
            for i, response in enumerate(step_responses):
                try:
                    logger.info(f"  📋 Step {i+1} response structure: {list(response.keys())}")
                    
                    # Try different possible keys for response data
                    response_data = None
                    for key in ['response_data', 'data', 'body', 'json', 'content']:
                        if key in response and response[key]:
                            response_data = response[key]
                            logger.info(f"  📋 Found response data in key '{key}': type={type(response_data)}")
                            break
                    
                    # If no standard key found, check if response itself is the API data
                    if response_data is None:
                        # Check if response has API-like structure (items, totalResults, etc.)
                        if 'items' in response or 'data' in response or len(response) > 0:
                            response_data = response
                            logger.info(f"  📋 Using response directly as API data: {list(response.keys())}")
                        else:
                            # Try to find the first dict value that looks like API response data
                            for key, value in response.items():
                                if isinstance(value, dict) and len(value) > 0:
                                    response_data = value
                                    logger.info(f"  📋 Using response key '{key}' as data: {list(value.keys())}")
                                    break
                    
                    if response_data and isinstance(response_data, dict):
                        logger.info(f"  📋 Response data keys: {list(response_data.keys())}")
                        
                        # Look for direct match
                        if param_name in response_data:
                            value = str(response_data[param_name])
                            logger.info(f"  ✅ Found {param_name}={value} in step {i+1} response")
                            self._cache_parameter_value(param_name, value)
                            return value
                        
                        # Look for ID-like fields in nested objects
                        logger.info(f"  🔍 Searching for {param_name} in nested response data...")
                        value = self._extract_id_from_response(response_data, param_name)
                        if value:
                            logger.info(f"  ✅ Extracted {param_name}={value} from step {i+1} response")
                            self._cache_parameter_value(param_name, value)
                            return value
                        else:
                            logger.info(f"  ❌ Could not extract {param_name} from step {i+1} response")
                    else:
                        logger.warning(f"  ❌ No valid response_data found in step {i+1}")
                            
                except Exception as e:
                    logger.warning(f"  ⚠️  Error processing step {i+1} response: {e}")
                    continue
        else:
            logger.warning(f"  ❌ No step_responses provided to resolve_not_sure_parameter")
        
        logger.warning(f"  ❌ Could not resolve %not-sure% parameter {param_name} from step responses")
        return None
    
    def _cache_parameter_value(self, param_name: str, value: str):
        """Cache a parameter value for future use"""
        if param_name not in self.available_ids_cache:
            self.available_ids_cache[param_name] = []
        if value not in self.available_ids_cache[param_name]:
            self.available_ids_cache[param_name].append(value)
    
    def _extract_id_from_response(self, response_data: dict, param_name: str) -> Optional[str]:
        """
        Extract ID value from response data by looking for matching patterns
        """
        logger.info(f"    🔍 _extract_id_from_response: Looking for {param_name} in response with keys: {list(response_data.keys())}")
        
        # Direct match
        if param_name in response_data:
            result = str(response_data[param_name])
            logger.info(f"    ✅ Found direct match: {param_name}={result}")
            return result
        
        # Look for array of objects with ID fields
        for key, value in response_data.items():
            logger.info(f"    🔍 Checking key '{key}' with type {type(value)}")
            
            if isinstance(value, list) and value:
                logger.info(f"    📋 Found array '{key}' with {len(value)} items")
                # Check first item in array
                first_item = value[0]
                if isinstance(first_item, dict):
                    logger.info(f"    📋 First item keys: {list(first_item.keys())}")
                    
                    # Look for exact param name
                    if param_name in first_item:
                        result = str(first_item[param_name])
                        logger.info(f"    ✅ Found exact param match in array item: {param_name}={result}")
                        return result
                    
                    # Look for common ID patterns
                    for id_key in ['id', 'Id', 'ID']:
                        if id_key in first_item:
                            # Match based on naming convention with flexible matching
                            param_root = param_name.lower().rstrip('id')  # billId -> bill
                            key_root = key.lower().rstrip('s')           # items -> item, bills -> bill
                            logger.info(f"    🔍 Matching '{param_root}' with '{key_root}' for id_key '{id_key}'")
                            
                            # Multiple matching strategies
                            is_match = False
                            
                            # 1. Exact match: bill == bill
                            if param_root == key_root:
                                is_match = True
                                logger.info(f"    ✅ Exact match: {param_root} == {key_root}")
                            
                            # 2. Starts with: bill.startswith(bil)
                            elif param_root.startswith(key_root) or key_root.startswith(param_root):
                                is_match = True
                                logger.info(f"    ✅ Prefix match: {param_root} <-> {key_root}")
                            
                            # 3. Common containers: items, data, results, list
                            elif key.lower() in ['items', 'data', 'results', 'list', 'records']:
                                is_match = True
                                logger.info(f"    ✅ Common container match: {key}")
                            
                            # 4. Fuzzy match: check if param_root is similar to key_root
                            elif len(param_root) >= 3 and len(key_root) >= 3:
                                # Check if they share a common prefix of at least 3 chars
                                common_len = 0
                                for j in range(min(len(param_root), len(key_root))):
                                    if param_root[j] == key_root[j]:
                                        common_len += 1
                                    else:
                                        break
                                if common_len >= 3:
                                    is_match = True
                                    logger.info(f"    ✅ Fuzzy match: {param_root} ~ {key_root} (common: {common_len})")
                            
                            if is_match:
                                result = str(first_item[id_key])
                                logger.info(f"    ✅ Found ID match: {param_name} -> {key}[0].{id_key} = {result}")
                                return result
                            
            elif isinstance(value, dict):
                logger.info(f"    🔍 Recursing into nested object '{key}'")
                # Recursively search in nested objects
                nested_result = self._extract_id_from_response(value, param_name)
                if nested_result:
                    logger.info(f"    ✅ Found in nested object: {nested_result}")
                    return nested_result
        
        logger.info(f"    ❌ No match found for {param_name}")
        return None
    
    def _fetch_value_from_dependency_endpoint(self, dep_endpoint: str, param_name: str) -> Optional[str]:
        """
        Fetch a value for param_name from a dependency endpoint
        """
        logger.info(f"    🌐 Fetching {param_name} from dependency endpoint: {dep_endpoint}")
        
        try:
            # Create a basic step for dependency endpoint
            dep_step = {
                'endpoint': dep_endpoint,
                'method': 'GET',
                'query_parameters': {},
                'request_body': {},
                'path_variables': {},
                'data_dependencies': {}
            }
            
            # Execute the dependency endpoint
            response = self.execute_request(dep_step, test_data_row=None, current_step=0, step_responses=[])
            
            if response and response.get('success') and 'response_body' in response:
                response_body = response['response_body']
                
                # Try to extract the parameter value from response
                value = self._extract_param_from_response(response_body, param_name)
                if value is not None:
                    logger.info(f"    ✅ Extracted {param_name}={value} from {dep_endpoint}")
                    return value
                else:
                    logger.info(f"    ⚠️  Could not extract {param_name} from response")
                    
            else:
                logger.warning(f"    ❌ Failed to get valid response from {dep_endpoint}")
                
        except Exception as e:
            logger.error(f"    ❌ Error fetching from {dep_endpoint}: {e}")
            
        return None
    
    def _extract_param_from_response(self, response_body: Any, param_name: str) -> Optional[str]:
        """
        Extract parameter value from API response
        """
        if not response_body:
            return None
            
        try:
            # If response is a list, get the first item
            if isinstance(response_body, list) and len(response_body) > 0:
                response_body = response_body[0]
            
            # If response is a dict with 'items' array (paginated response)
            if isinstance(response_body, dict) and 'items' in response_body:
                items = response_body['items']
                if isinstance(items, list) and len(items) > 0:
                    response_body = items[0]
            
            # Try to extract the parameter directly
            if isinstance(response_body, dict):
                # Direct parameter match
                if param_name in response_body:
                    return str(response_body[param_name])
                
                # Try common ID field names
                id_fields = ['id', 'Id', 'ID']
                for field in id_fields:
                    if field in response_body:
                        return str(response_body[field])
                
                # Try parameter-specific patterns
                # e.g., billId -> look for 'billId' or 'id' in bill context
                if param_name.endswith('Id'):
                    base_name = param_name[:-2].lower()  # Remove 'Id'
                    for key in response_body:
                        if key.lower() == base_name + 'id' or key.lower() == 'id':
                            return str(response_body[key])
                            
        except Exception as e:
            logger.error(f"    ❌ Error extracting {param_name} from response: {e}")
            
        return None

    def merge_test_data(self, base_params: Dict, base_body: Dict, test_data_row: Dict, endpoint: str = "", path_vars: Dict = None, data_for: str = "params") -> tuple:
        """Merge test data row with base parameters and body, filtering relevant parameters"""
        # Start with resolved params to keep dependencies, but filter out null base params later
        merged_params = base_params.copy()
        merged_body = base_body.copy()
        
        # Skip metadata fields
        metadata_fields = {'index', 'expected_status_code', 'expected_code', 'reason'}
        
        # Get path variable names
        path_var_names = set()
        if path_vars:
            path_var_names = set(path_vars.keys())
        
        # Store path variables from CSV for later use as fallback
        csv_path_vars = {}
        
        # Store parameters that need dependency resolution  
        not_sure_params = {}
        
        # Handle None test_data_row
        if test_data_row is None:
            return merged_params, merged_body, csv_path_vars, not_sure_params
        
        def apply_kv(k, v, target):
            if target == "params":
                merged_params[k] = v
            else:  # target == "body"
                if isinstance(merged_body, dict):
                    merged_body[k] = v
        
        # NEW: Extract path variables from CSV for fallback use
        def extract_path_vars_from_data(data_dict):
            for param_key, param_value in data_dict.items():
                if param_key in path_var_names and param_value is not None:
                    # Check for %not-sure% marker
                    if param_value == "%not-sure%":
                        not_sure_params[param_key] = True
                        logger.info(f"  🔍 Found %not-sure% marker for path variable {param_key}")
                    else:
                        csv_path_vars[param_key] = param_value
                        logger.info(f"  📋 Stored CSV path variable {param_key}={param_value} for fallback")
        
        # nếu test_data_row là dict 2 lớp {"param": {...}, "body": {...}}
        if "param" in test_data_row or "body" in test_data_row:
            logger.info(f"  📋 Processing nested test data structure with param/body keys")
            for k, v in (test_data_row.get("param") or {}).items():
                if k not in metadata_fields and k and v is not None:
                    if k == 'data' and isinstance(v, str):
                        logger.info(f"  🔍 Processing nested 'data' field with JSON content: {v[:100]}...")
                        try:
                            # Parse JSON data
                            data_obj = json.loads(v)
                            if isinstance(data_obj, dict) and 'data' in data_obj:
                                logger.info(f"  📦 Found nested data structure, extracting parameters...")
                                # Extract actual parameters from nested data
                                actual_data = data_obj['data']
                                # Check if actual_data is None
                                if actual_data is not None and isinstance(actual_data, dict):
                                    # Extract path variables for fallback
                                    extract_path_vars_from_data(actual_data)
                                    # Process non-path variables normally
                                    for param_key, param_value in actual_data.items():
                                        if param_key not in path_var_names and param_value is not None:
                                            logger.info(f"  ✅ Adding parameter {param_key}={param_value} from nested JSON data")
                                            apply_kv(param_key, param_value, "params")
                            elif isinstance(data_obj, dict):
                                logger.info(f"  📋 Found direct data object, extracting parameters...")
                                # Direct data object
                                # Extract path variables for fallback
                                extract_path_vars_from_data(data_obj)
                                # Process non-path variables normally
                                for param_key, param_value in data_obj.items():
                                    if param_key not in path_var_names and param_value is not None:
                                        logger.info(f"  ✅ Adding parameter {param_key}={param_value} from direct JSON data")
                                        apply_kv(param_key, param_value, "params")
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON in nested data field: {v}")
                        # Skip further processing of the 'data' field after JSON parsing
                        logger.info(f"  🛑 Skipping further processing of nested 'data' key to avoid duplication")
                        continue
                    else:
                        if k not in path_var_names:
                            apply_kv(k, v, "params")
                        else:
                            csv_path_vars[k] = v
                            logger.info(f"  📋 Stored CSV path variable {k}={v} for fallback")
            for k, v in (test_data_row.get("body") or {}).items():
                if k not in metadata_fields and k and v is not None:
                    if k not in path_var_names:  # Skip path variables
                        apply_kv(k, v, "body")
            return merged_params, merged_body, csv_path_vars, not_sure_params
        
        
        # Determine which parameters are valid for this endpoint
        valid_params = set()
        endpoint_clean = endpoint.lower().replace('get-', '').replace('post-', '').replace('put-', '').replace('delete-', '')
        
        # TODO: Define endpoint_param_mapping or implement proper parameter validation
        # For now, disable parameter filtering to allow JSON parsing to work correctly
        # for pattern, params in endpoint_param_mapping.items():
        #     if pattern in endpoint_clean:
        #         valid_params.update(params)
        #         break
            
        for key, value in test_data_row.items():
            if key in metadata_fields or not key:
                continue
            # Skip only None values, but keep empty strings for testing invalid params
            if value is None:
                continue
                
            # Special handling for 'data' field which contains JSON
            if key == 'data' and isinstance(value, str):
                logger.info(f"  🔍 Processing 'data' field with JSON content: {value[:100]}...")
                try:
                    # Parse JSON data
                    data_obj = json.loads(value)
                    if isinstance(data_obj, dict) and 'data' in data_obj:
                        logger.info(f"  📦 Found nested data structure, extracting parameters...")
                        # Extract actual parameters from nested data
                        actual_data = data_obj['data']
                        # Check if actual_data is None
                        if actual_data is not None and isinstance(actual_data, dict):
                            # Extract path variables for fallback
                            extract_path_vars_from_data(actual_data)
                            # Process non-path variables normally
                            for param_key, param_value in actual_data.items():
                                # Skip path variables from params/body as they are stored separately for fallback
                                if param_key not in path_var_names and param_value is not None:
                                    logger.info(f"  ✅ Adding parameter {param_key}={param_value} from JSON data")
                                    apply_kv(param_key, param_value, data_for)
                    elif isinstance(data_obj, dict):
                        logger.info(f"  📋 Found direct data object, extracting parameters...")
                        # Direct data object
                        # Extract path variables for fallback
                        extract_path_vars_from_data(data_obj)
                        # Process non-path variables normally
                        for param_key, param_value in data_obj.items():
                            # Skip path variables from params/body as they are stored separately for fallback
                            if param_key not in path_var_names and param_value is not None:
                                logger.info(f"  ✅ Adding parameter {param_key}={param_value} from JSON data")
                                apply_kv(param_key, param_value, data_for)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON in data field: {value}")
                # Skip further processing of the 'data' field after JSON parsing
                logger.info(f"  🛑 Skipping further processing of 'data' key to avoid duplication")
                continue
            else:
                # Store path variables for fallback use instead of skipping
                if key in path_var_names:
                    csv_path_vars[key] = value
                    logger.info(f"  📋 Stored CSV path variable {key}={value} for fallback")
                    continue
                # Since endpoint parameter validation is disabled, allow all non-metadata parameters
                if True:  # Temporarily allow all parameters
                    # Try to convert string numbers to appropriate types
                    if isinstance(value, str):
                        if value.isdigit():
                            value = int(value)
                        elif value.replace('.', '').isdigit():
                            value = float(value)
                        elif value.lower() in ['true', 'false']:
                            value = value.lower() == 'true'
                    
                    # Add to params or body based on data_for
                    apply_kv(key, value, data_for)
        
        # Filter out null parameters that weren't provided in test data
        # but keep non-null resolved dependencies
        if test_data_row:
            test_data_keys = set()
            # Collect all keys that were actually provided in test data
            for key, value in test_data_row.items():
                if key not in metadata_fields and key and value is not None:
                    if key == 'data' and isinstance(value, str):
                        try:
                            data_obj = json.loads(value)
                            if isinstance(data_obj, dict):
                                if 'data' in data_obj and data_obj['data']:
                                    test_data_keys.update(data_obj['data'].keys())
                                else:
                                    test_data_keys.update(data_obj.keys())
                        except json.JSONDecodeError:
                            pass
                    else:
                        test_data_keys.add(key)
            
            # Remove null params that weren't in test data (but keep non-null dependencies)
            filtered_params = {}
            for key, value in merged_params.items():
                if value is not None or key in test_data_keys:
                    filtered_params[key] = value
            merged_params = filtered_params
        return merged_params, merged_body, csv_path_vars, not_sure_params
    
    def execute_request(self, step: Dict, test_data_row: Optional[Dict] = None, current_step: int = 1, step_responses: List[Dict] = None) -> Dict:
        """Execute a single API request step"""
        endpoint = step.get('endpoint', '')
        method = step.get('method', 'GET').upper()
        base_params = step.get('query_parameters', {})
        base_body = step.get('request_body', {})
        path_vars = step.get('path_variables', {})
        data_deps = step.get('data_dependencies', {})
        
        # Resolve data dependencies (PRIORITY 1)
        if step_responses is None:
            step_responses = []
        resolved_params, resolved_body = self.resolve_dependencies(base_params, base_body, data_deps, current_step, step_responses)
        
        # Merge with test data and extract CSV path variables (PRIORITY 2)
        csv_path_vars = {}
        not_sure_params = {}
        if test_data_row:
            data_for = "params" if method in ["GET", "DELETE"] else "body"
            logger.info(f"  🔄 Calling merge_test_data with test_data_row: {test_data_row}")
            resolved_params, resolved_body, csv_path_vars, not_sure_params = self.merge_test_data(resolved_params, resolved_body, test_data_row, endpoint, path_vars, data_for=data_for)
            logger.info(f"  🔄 After merge_test_data - resolved_params: {resolved_params}")
            logger.info(f"  🔄 CSV path variables available: {csv_path_vars}")
            logger.info(f"  🔍 Parameters needing dependency resolution: {not_sure_params}")
        
        # Clean endpoint format
        clean_endpoint = endpoint
        if clean_endpoint.startswith(('get-', 'post-', 'put-', 'delete-', 'patch-')):
            clean_endpoint = clean_endpoint.split('-', 1)[1]
        
        # Replace path variables in endpoint
        final_endpoint = clean_endpoint
        all_path_vars = path_vars.copy()
        
        # PRIORITY 1: Add CSV path variables (from test data)
        for k, v in csv_path_vars.items():
            if f'{{{k}}}' in final_endpoint and v is not None:
                all_path_vars[k] = v
                logger.info(f"  📋 Using CSV test data value for path variable {k}={v}")
        
        # PRIORITY 2: Add resolved dependencies that are used as path variables
        for k, v in resolved_params.items():
            if f'{{{k}}}' in final_endpoint:
                # Only override if we don't already have a value from CSV
                if k not in all_path_vars or all_path_vars[k] is None:
                    all_path_vars[k] = v
                    logger.info(f"  🎯 Using dependency value for path variable {k}={v}")
                else:
                    logger.info(f"  📋 Keeping CSV value {k}={all_path_vars[k]} instead of dependency value {v}")
        
        # Handle missing path variables with improved fallback strategy
        missing_path_vars = []
        for var in re.findall(r'\{(\w+)\}', final_endpoint):
            if var not in all_path_vars or all_path_vars[var] is None:
                missing_path_vars.append(var)
        
        # Handle %not-sure% parameters by resolving dependencies
        for param_name in not_sure_params:
            # Only resolve if we don't already have a concrete value
            if param_name not in all_path_vars or all_path_vars[param_name] is None:
                resolved_value = self.resolve_not_sure_parameter(param_name, endpoint, step_responses)
                if resolved_value is not None:
                    all_path_vars[param_name] = resolved_value
                    logger.info(f"🔍 Resolved %not-sure% parameter {param_name}={resolved_value}")
                else:
                    logger.warning(f"⚠️  Could not resolve %not-sure% parameter {param_name}")
            else:
                logger.info(f"📋 %not-sure% parameter {param_name} already has value: {all_path_vars[param_name]}")
        
        if missing_path_vars:
            logger.warning(f"❌ Missing path variables: {missing_path_vars}")
            fallback_values = {}
            
            for var in missing_path_vars:
                # PRIORITY 0: Skip if this was a %not-sure% parameter (should have been resolved above)
                if var in not_sure_params:
                    logger.warning(f"⚠️  Skipping unresolved %not-sure% parameter {var}")
                    continue
                
                # PRIORITY 1: Use cached IDs from previous responses (existing logic)
                if var in self.available_ids_cache and self.available_ids_cache[var]:
                    fallback_values[var] = self.available_ids_cache[var][0]
                    logger.info(f"🎯 Using cached dependency value for {var}: {fallback_values[var]}")
                # PRIORITY 2: Generic fallback (reduced from previous)
                else:
                    if 'id' in var.lower() or var.lower().endswith('id'):
                        fallback_values[var] = '1'
                    else:
                        fallback_values[var] = 'default'
                    logger.info(f"🔄 Using generic fallback value for {var}: {fallback_values[var]}")
            
            for var in missing_path_vars:
                if var in fallback_values:
                    all_path_vars[var] = fallback_values[var]
        
        # Remove path variables from query parameters
        final_params = resolved_params.copy()
        for var, value in all_path_vars.items():
            if value is not None:
                final_endpoint = final_endpoint.replace(f'{{{var}}}', str(value))
                # Remove from query params if it was used as path variable
                if var in final_params:
                    del final_params[var]
        
        # Build full URL
        url = f"{self.base_url}{final_endpoint}"
        
        # Build full URL with query string for debugging
        # Build full URL with query string for debugging
# -> BỎ param nếu None hoặc chuỗi rỗng
        # Build full URL with query string for debugging
        if final_params:
            clean_params = {}
            for key, value in final_params.items():
                if value is None:
                    # null => bỏ khỏi query
                    continue
                # "" (empty string) vẫn giữ lại
                clean_params[key] = value

            # Log URL đầy đủ
            if clean_params:
                query_parts = []
                for k, v in clean_params.items():
                    if v == "":
                        query_parts.append(f"{k}=")  # chuỗi rỗng
                    else:
                        query_parts.append(f"{k}={v}")
                query_string = "&".join(query_parts)
                full_url_with_query = f"{url}?{query_string}"
            else:
                full_url_with_query = url

            # Dùng params đã làm sạch để gửi request
            final_params = clean_params
        else:
            full_url_with_query = url


        
        # Debug logging for URL construction
        logger.info(f"  🔗 URL Construction:")
        logger.info(f"    Original endpoint: {clean_endpoint}")
        logger.info(f"    Final endpoint: {final_endpoint}")
        logger.info(f"    Base URL: {url}")
        logger.info(f"    Full URL with query: {full_url_with_query}")
        if all_path_vars:
            logger.info(f"    Path variables: {all_path_vars}")
        if final_params:
            logger.info(f"    Query parameters: {final_params}")
        
        # Prepare request
        request_kwargs = {
            'timeout': 30,
        }
        
        # Add authentication header if we have a token
        if self.auth_token:
            request_kwargs['headers'] = {'Authorization': f'Bearer {self.auth_token}'}
            logger.info(f"🔑 Using Bearer token for {clean_endpoint}")
        
        if method in ['GET', 'DELETE']:
            request_kwargs['params'] = final_params
        else:
            request_kwargs['json'] = resolved_body
            if final_params:
                request_kwargs['params'] = final_params
        
        # Execute request
        start_time = time.time()
        try:
            response = self.session.request(method, url, **request_kwargs)
            execution_time = time.time() - start_time
            
            # Try to parse JSON response
            try:
                response_json = response.json()
            except:
                response_json = response.text
            
            # Cache successful responses for dependencies
            if response.status_code < 400:
                cache_key = f"{method}_{final_endpoint}"
                self.response_cache[cache_key] = response_json
            
            return {
                'url': full_url_with_query,
                'status_code': response.status_code,
                'response': response_json,
                'execution_time': execution_time,
                'success': response.status_code < 400,
                'error': None,
                'merged_params': final_params,
                'merged_body': resolved_body
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'url': full_url_with_query,
                'status_code': None,
                'response': None,
                'execution_time': execution_time,
                'success': False,
                'error': str(e),
                'merged_params': final_params,
                'merged_body': resolved_body
            }
    
    def run_test_case(self, test_case_file: Path) -> bool:
        """Run a single test case with its test data"""
        logger.info(f"Running test case: {test_case_file.name}")
        is_pass = False
        # Load test case
        with open(test_case_file, 'r') as f:
            test_case = json.load(f)
        
        test_case_id = test_case_file.stem
        target_endpoint = test_case.get('test_case', {}).get('endpoint', '')
        
        # Không reset cache nữa - dùng global cache
        logger.info(f"🎯 Target endpoint: {target_endpoint}")
        steps = test_case.get('test_case', {}).get('steps', [])
        
        # Create output directory for this test case
        test_case_output_dir = self.output_dir / f"{test_case_id}_response"
        test_case_output_dir.mkdir(exist_ok=True)
        
        if not steps:
            logger.warning(f"No steps found in test case: {test_case_id}")
            return is_pass
        
        # Find test data files (both param and body)
        endpoint_identifier = test_case_id.replace('_0_1', '').replace('_1_1', '').replace('_2_1', '')
        files = self.find_test_data_files(endpoint_identifier)
        
        # Load param and body data separately
        param_rows = self.load_test_data(files["param"]) if files["param"] else []
        body_rows = self.load_test_data(files["body"]) if files["body"] else []
        
        # Log what we found
        if files["param"]:
            logger.info(f"📄 Param CSV: {files['param'].name} -> {len(param_rows)} rows")
        if files["body"]:
            logger.info(f"📄 Body  CSV: {files['body'].name}  -> {len(body_rows)} rows")
        
        # Create combined test data rows
        if not param_rows and not body_rows:
            test_data_rows = [{}]
            logger.info(f"🧪 No test data found, will run 1 time with empty data")
        else:
            # Sync row count: take max length, pad with {} for missing rows
            max_len = max(len(param_rows), len(body_rows))
            test_data_rows = []
            for i in range(max_len):
                test_data_rows.append({
                    "param": param_rows[i] if i < len(param_rows) else {},
                    "body":  body_rows[i]  if i < len(body_rows)  else {}
                })
            logger.info(f"🧪 Will run {len(test_data_rows)} times (combining param/body rows by index)")
        
        # Run each step with each test data row
        for data_row_idx, test_data_row in enumerate(test_data_rows):
            logger.info(f"Running with test data row {data_row_idx + 1}/{len(test_data_rows)}")
            
            # Handle None test data row
            if test_data_row is None:
                logger.warning(f"Skipping None test data row {data_row_idx + 1}")
                continue
                
            # Extract expected status for this test data row
            expected_status = self.extract_expected_status(test_data_row)
            logger.info(f"  🎯 Expected status extracted: {expected_status} from test_data_row: {test_data_row}")
            
            # Store responses from previous steps for dependency resolution
            step_responses = []
            
            for step_idx, step in enumerate(steps):
                step_endpoint = step.get('endpoint', '')
                is_target_step = (step_endpoint == target_endpoint)
                
                result = self.execute_request(step, test_data_row, step_idx + 1, step_responses)
                
                # Store successful response for dependencies
                if result['success'] and result['response']:
                    step_responses.append(result['response'])
                else:
                    step_responses.append(None)
                
                # Chỉ assert/validate target endpoint, skip dependency steps
                if not is_target_step:
                    logger.info(f"  🔄 Step {step_idx + 1}: {step.get('method', 'GET')} {step_endpoint} -> {result['status_code']} (dependency - không assert)")
                    continue
                
                # Determine pass/fail chỉ cho target endpoint
                actual_status = result['status_code']
                if actual_status is not None:
                    is_pass = self.is_status_match(actual_status, expected_status)
                else:
                    is_pass = False
                
                # Save response to individual file (chỉ cho target endpoint)
                response_filename = f"row_{data_row_idx + 1}_target_response.json"
                response_file_path = test_case_output_dir / response_filename
                
                response_data = {
                    'test_case_id': test_case_id,
                    'target_endpoint': target_endpoint,
                    'step_number': step_idx + 1,
                    'data_row': data_row_idx + 1,
                    'request': {
                        'url': result.get('url', ''),
                        'method': step.get('method', 'GET'),
                        'endpoint': step.get('endpoint', ''),
                        'base_query_parameters': step.get('query_parameters', {}),
                        'merged_query_parameters': result.get('merged_params', {}),
                        'base_request_body': step.get('request_body', {}),
                        'merged_request_body': result.get('merged_body', {}),
                        'test_data_used': test_data_row
                    },
                    'response': {
                        'status_code': result['status_code'],
                        'body': result['response'],
                        'execution_time': f"{result['execution_time']:.3f}s",
                        'success': result['success'],
                        'error': result.get('error')
                    },
                    'validation': {
                        'expected_status': expected_status,
                        'actual_status': actual_status,
                        'status_match': is_pass,
                        'test_result': 'PASS' if is_pass else 'FAIL'
                    }
                }
                
                with open(response_file_path, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, indent=2, ensure_ascii=False)
                
                # Log to CSV (chỉ target endpoint)
                self.csv_writer.writerow({
                    'test_case_id': test_case_id,
                    'step_number': step_idx + 1,
                    'endpoint': step.get('endpoint', ''),
                    'method': step.get('method', 'GET'),
                    'test_data_row': data_row_idx + 1,
                    'request_params': json.dumps(result.get('merged_params', {})),
                    'request_body': json.dumps(result.get('merged_body', {})),
                    'final_url': result.get('url', ''),
                    'response_status': result['status_code'],
                    'expected_status': expected_status,
                    'execution_time': f"{result['execution_time']:.3f}s",
                    'status': 'PASS' if is_pass else 'FAIL'
                })
                
                # Console logging cho target endpoint
                status_emoji = "✅" if is_pass else "❌"
                expected_info = f"(expected: {expected_status})" if expected_status != '2xx' else ""
                logger.info(f"  {status_emoji} 🎯 TARGET: {step.get('method', 'GET')} {step.get('endpoint', '')} -> {result['status_code']} {expected_info} ({result['execution_time']:.3f}s)")
                
                if not is_pass:
                    logger.error(f"    Expected: {expected_status}, Got: {actual_status}")
                    if result.get('error'):
                        logger.error(f"    Error: {result.get('error')}")
                    if result['response']:
                        logger.error(f"    Response: {json.dumps(result['response'], indent=2)}")
                # Small delay between requests
                time.sleep(0.1)
        return is_pass
    
    def auto_discover_dependencies(self):
        """Auto-discover dependency endpoints from test cases"""
        dependency_endpoints = set()
        dependency_mappings = {}
        
        # Scan all test case files to find dependencies
        if not self.test_case_dir.exists():
            return dependency_endpoints, dependency_mappings
            
        for test_file in self.test_case_dir.glob("*.json"):
            try:
                with open(test_file, 'r') as f:
                    test_case = json.load(f)
                
                steps = test_case.get('test_case', {}).get('steps', [])
                for step in steps:
                    # Find steps with dependencies
                    data_deps = step.get('data_dependencies', {})
                    if data_deps:
                        from_step = None
                        for dep_key, dep_info in data_deps.items():
                            if isinstance(dep_info, dict) and 'from_step' in dep_info:
                                from_step_idx = dep_info['from_step'] - 1  # Convert to 0-based
                                if 0 <= from_step_idx < len(steps):
                                    dep_endpoint = steps[from_step_idx].get('endpoint', '')
                                    if dep_endpoint:
                                        dependency_endpoints.add(dep_endpoint)
                                        # Store mapping: dependency_key -> source_endpoint
                                        dependency_mappings[dep_key] = dep_endpoint
                                        
            except Exception as e:
                logger.debug(f"Error scanning {test_file.name}: {e}")
                
        return dependency_endpoints, dependency_mappings
    
    def extract_ids_from_response(self, response_data, endpoint):
        """Generic function to extract IDs from API response"""
        ids = []
        
        if isinstance(response_data, list):
            # Direct array of objects
            for item in response_data:
                if isinstance(item, dict) and 'id' in item:
                    ids.append(item['id'])
        elif isinstance(response_data, dict):
            # Check common patterns for nested arrays
            for key in ['data', 'items', 'results', 'holidays', 'provinces', 'brands', 'categories', 'products']:
                if key in response_data and isinstance(response_data[key], list):
                    for item in response_data[key]:
                        if isinstance(item, dict) and 'id' in item:
                            ids.append(item['id'])
                    break
            # If no nested array, check if response itself has ID
            if not ids and 'id' in response_data:
                ids.append(response_data['id'])
        
        return ids
    
    def convert_endpoint_to_url(self, endpoint):
        """Convert test case endpoint format to actual URL"""
        # Remove method prefix if exists
        if '-' in endpoint and endpoint.split('-')[0].upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            clean_endpoint = endpoint.split('-', 1)[1]
        else:
            clean_endpoint = endpoint
            
        # Build full URL
        url = f"{self.base_url}{clean_endpoint}"
        
        # Remove path variables for dependency endpoints (use base collection endpoint)
        # /brands/{brandId} -> /brands
        url = re.sub(r'/\{[^}]+\}$', '', url)
        
        return url
    
    def preload_dependencies(self):
        """Generic dependency preloading based on auto-discovery"""
        logger.info("🔄 Auto-discovering and preloading dependencies...")
        
        # Auto-discover dependency endpoints from test cases
        dependency_endpoints, dependency_mappings = self.auto_discover_dependencies()
        
        if not dependency_endpoints:
            logger.info("🔍 No dependencies found in test cases")
            return
            
        logger.info(f"🔍 Found {len(dependency_endpoints)} dependency endpoints: {list(dependency_endpoints)}")
        
        # Preload each dependency endpoint with progress
        total_endpoints = len(dependency_endpoints)
        for i, endpoint in enumerate(dependency_endpoints, 1):
            try:
                url = self.convert_endpoint_to_url(endpoint)
                logger.info(f"📡 Preloading ({i}/{total_endpoints}): {endpoint}")
                logger.info(f"    🌐 URL: {url}")
                
                # Reduced timeout and added progress indication
                import time
                start_time = time.time()
                
                response = self.session.get(url, timeout=10)  # Reduced from 30 to 10 seconds
                
                elapsed = time.time() - start_time
                logger.info(f"    ⏱️  Response time: {elapsed:.2f}s")
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Cache response data
                    cache_key = endpoint.replace('get-', '').replace('/', '_').strip('_')
                    self.global_dependency_cache[cache_key] = response_data
                    
                    # Extract IDs
                    ids = self.extract_ids_from_response(response_data, endpoint)
                    if ids:
                        # Map to dependency keys that use this endpoint
                        for dep_key, dep_endpoint in dependency_mappings.items():
                            if dep_endpoint == endpoint:
                                self.available_ids_cache[dep_key] = ids
                                logger.info(f"    📋 Cached {len(ids)} IDs for {dep_key}: {ids[:3] if len(ids) > 3 else ids}...")
                    
                    logger.info(f"    ✅ Success ({response.status_code})")
                else:
                    logger.warning(f"    ❌ Failed ({response.status_code}): {response.text[:100]}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"    ⏰ Timeout (>10s) for {endpoint} - skipping")
            except requests.exceptions.ConnectionError:
                logger.warning(f"    🔌 Connection error for {endpoint} - skipping")
            except Exception as e:
                logger.warning(f"    ❌ Error: {str(e)[:100]}")
        
        logger.info(f"✅ Preloading complete: {len(self.global_dependency_cache)} endpoints cached")

    def run_all(self):
        """Run all test cases or specific endpoint"""
        logger.info(f"Starting test execution for service: {self.service_name}")
        
        
        # Find test case files
        test_case_files = self.find_test_case_files(self.endpoint)
        
        if not test_case_files:
            logger.error("No test case files found!")
            return
        
        # Sort by topolist order if available
        topolist = self.load_topolist()
        if topolist:
            # Sort files based on topolist order
            def sort_key(file_path):
                filename = file_path.stem
                logger.debug(f"🔍 Sorting filename: {filename}")
                
                for i, endpoint in enumerate(topolist):
                    # Extract method and path from endpoint
                    if '-' in endpoint:
                        method, path = endpoint.split('-', 1)
                        
                        # Convert path to match filename pattern
                        # /brands/{brandId} -> _brands_brandId_
                        path_pattern = path.replace('/', '_').replace('{', '').replace('}', '_')
                        
                        # Create multiple possible patterns
                        patterns = [
                            f"{path_pattern}",  # Basic pattern
                            f"{method.lower()}{path_pattern}",  # with method prefix
                            f"{path_pattern}{method}",  # with method suffix  
                            f"{path_pattern}{method.title()}",  # with method suffix capitalized
                        ]
                        
                        # Check if any pattern matches filename
                        for pattern in patterns:
                            if pattern in filename:
                                logger.debug(f"  ✅ Match found: {endpoint} (index {i}) -> pattern '{pattern}' in '{filename}'")
                                return i
                                
                logger.debug(f"  ❌ No match found for: {filename}")
                return len(topolist)  # Put unmatched files at the end
            
            logger.info("📋 Sorting test cases by topolist order...")
            test_case_files.sort(key=sort_key)
        
        # Execute test cases    
        total_files = len(test_case_files)
        count_pass = 0
        total_files = 0
        for i, test_case_file in enumerate(test_case_files, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Test Case {i}/{total_files}: {test_case_file.name}")
            logger.info(f"{'='*60}")
            total_files += 1
            try:
                is_pass = self.run_test_case(test_case_file)
                if is_pass:
                    count_pass += 1
                    continue
            except Exception as e:
                logger.error(f"Error running test case {test_case_file.name}: {e}")
            
        logger.info(f"\n🎉 Test execution completed! Results saved to CSV. {count_pass}/{total_files} tests passed")
        logger.info(f"Success rate: {count_pass/total_files*100:.2f}%")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.csv_file:
            self.csv_file.close()
        self.session.close()

def main():
    service = "Bill"
    base_url = "https://bills-api.parliament.uk"
    token = None
    # sequence_runner = SequenceRunner(service, base_url, token, endpoint)
    # sequence_runner.run_all()

    # service = "Canada Holidays"
    # base_url = "https://canada-holidays.ca"
    # token = None

    sequence_runner = SequenceRunner(service, base_url, token)
    sequence_runner.run_all()
if __name__ == "__main__":
    main() 


# python sequence_runner.py --service "Canada Holidays"  --base-url https://canada-holidays.ca
#python sequence_runner.py --service "Bill"  --base-url https://bills-api.parliament.uk
#python sequence_runner.py --service "Pet Store"  --base-url https://petstore3.swagger.io/api/v3