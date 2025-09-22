

import copy
import json
import urllib
from urllib.parse import quote                      # For encoding URL

LOGGED = True
def lprint(*x): 
    if LOGGED: print(*x)
def jprint(x):
    if LOGGED: print(json.dumps(x))
class DataGeneratorUtils:
    @staticmethod
    def extract_json_data_from_text_data(text):
        data_items = []
        stack = []
        start_index = None
        
        for index, char in enumerate(text):
            if char in '{[':  # Handle both objects and arrays
                if not stack:
                    start_index = index
                stack.append(char)
            elif char in '}]':  # Handle both objects and arrays
                if stack and ((char == '}' and stack[-1] == '{') or (char == ']' and stack[-1] == '[')):
                    stack.pop()
                    if not stack and start_index is not None:
                        json_str = text[start_index:index + 1]
                        try:
                            obj = json.loads(json_str)
                            data_items.append(obj)
                            start_index = None  # Reset start_index after successful parse
                        except json.JSONDecodeError:
                            pass  # Handle the case where the JSON is invalid
                else:
                    # Handle the case where there might be nested objects or arrays
                    if stack:
                        stack.pop()
        
        return data_items
    #Trong quá trình sinh test data, có thể số lượng test case sinh ra cho phần 
    # parameter và requestBody là lệch nhau → cần cân bằng để ghép cặp khi kiểm thử.
    @staticmethod
    def balancing_test_data_item(param_data, body_data):
        if not param_data or not body_data:
            return param_data, body_data
        
        param_data_len = len(param_data)
        body_data_len = len(body_data)
        
        if param_data_len > body_data_len:
            n = param_data_len - body_data_len
            k = int(n / body_data_len)
            j = n % body_data_len
            
            copied_body_data = copy.deepcopy(body_data)
            for i in range(k):
                body_data += copied_body_data
            for i in range(j):
                body_data.append(body_data[i])
        else:
            n = body_data_len - param_data_len
            k = int(n / param_data_len)
            j = n % param_data_len
            
            copied_param_data = copy.deepcopy(param_data)
            for i in range(k):
                param_data += copied_param_data
            for i in range(j):
                param_data.append(param_data[i])
        return param_data, body_data
    
    @staticmethod

    def parse_jsonl_response( response: str, enc: bool = True) -> dict:
        """
        Parse the JSONL response from GPT model into JSON format

        Args:
            response (str): GPT's response
            enc (bool, optional): Encode the string value, used when data is generated for parameters. Defaults to True.

        Returns:
            dict: JSON array of data items
        """
        def _is_valid_jsonl(s: str):
            try:
                json.loads(s)
            except json.JSONDecodeError as e:
                print(f"[INFO] An error occurred when reading a JSONL data item: {e}")
                return False
            return True
        
        def filter_valid(s: str):
            if _is_valid_jsonl(s.strip()):
                return [s.strip()]
            else: 
                lines = s.split("\n")
                for i in reversed(range(len(lines))):
                    if not _is_valid_jsonl(lines[i]):
                        del lines[i]
                return lines
        
        lprint('[INFO] Origin response: \n', response)
        
        ans = None
        try:
            if '```json' in response:
                ans = response.split("```json")[1].split('```')[0]
            elif '```' in response: 
                ans = response.split("```")[1].split('```')[0]
        except:
            ans = response
            pass
        
        if ans is None:
            lprint("[INFO] Invalid response")
            return []
        
        lprint("[INFO] Parsing response...", ans)
        json_data = DataGeneratorUtils.extract_json_data_from_text_data(ans) 
        
        lprint("[INFO] Extracted JSON objects:", json_data)       
        
        # Encode parameter values because it appears in the URL
        if enc:
            # Change the list to string with comma as separator
            for i, item in enumerate(json_data):
                if item and isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, list):
                            json_data[i][key] = ",".join([str(v) for v in value])

            # Encode the string value
            for i, item in enumerate(json_data):
                if item:
                    for key, value in item.items():
                        json_data[i][key] = quote(value) if isinstance(value, str) else value

        return json_data
    import urllib.parse

def humanize_reason(reason: str) -> str:
    """
    Clean up the 'reason' text generated by LLM:
    - Decode URL-encoded sequences (e.g., %20 → space, %3D → =).
    - Remove prefixes like 'llm_success:' or 'llm_violation:'.
    - Trim leading/trailing whitespace.
    """
    if not reason:
        return reason

    # URL-decode
    decoded = urllib.parse.unquote(reason)

    # Remove known prefixes
    for prefix in ["llm_success:", "llm_violation:"]:
        if decoded.strip().lower().startswith(prefix):
            decoded = decoded[len(prefix):]

    return decoded.strip()
# data_generator_utils.py

# data_generator_utils.py
def collect_merged_parameters(swagger_spec: dict, path_str: str, method: str):
    path_item = swagger_spec.get('paths', {}).get(path_str, {}) or {}
    op_obj    = (path_item.get(method.lower(), {}) or {})

    path_params = path_item.get('parameters', []) or []
    op_params   = op_obj.get('parameters', []) or []

    merged = {}
    # path-level trước, op-level sau (op-level override)
    for p in path_params + op_params:
        key = (p.get('name'), p.get('in'))
        merged[key] = p
    return list(merged.values())
