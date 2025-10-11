export interface TestDataItem {
  request_params?: Record<string, any>;
  request_headers?: Record<string, string>;
  request_body?: Record<string, any> | string;
  expected_status_code?: number;
}

export interface VerifyTestDataRequest {
  test_data_items: TestDataItem[];
  timeout?: number;
}

export interface VerificationResult {
  script_id: string;
  script_type: string;
  passed: boolean;
  error_message?: string;
  execution_time?: number;
  script_output?: string;
}

export interface TestDataVerificationResult {
  test_data_index: number;
  overall_passed: boolean;
  results: VerificationResult[];
  total_execution_time?: number;
}

export interface VerifyTestDataResponse {
  endpoint_name: string;
  endpoint_id: string;
  total_test_data_items: number;
  overall_passed: boolean;
  verification_results: TestDataVerificationResult[];
  total_execution_time?: number;
}

export interface RequestResponsePair {
  request: Record<string, any>;
  response: Record<string, any>;
}

export interface VerifyRequestResponseRequest {
  request_response_pairs: RequestResponsePair[];
  timeout?: number;
}

export interface ValidationScriptResult {
  script_id: string;
  script_type: string;
  passed: boolean;
  error_message?: string;
  execution_time?: number;
  script_output?: string;
}

export interface RequestResponseVerificationResult {
  pair_index: number;
  overall_passed: boolean;
  results: ValidationScriptResult[];
  total_execution_time?: number;
}

export interface VerifyRequestResponseResponse {
  endpoint_name: string;
  endpoint_id: string;
  total_pairs: number;
  overall_passed: boolean;
  verification_results: RequestResponseVerificationResult[];
  total_execution_time?: number;
}
