export interface TestData {
  id: string;
  endpoint_id: string;
  name: string;
  description: string;
  request_params?: Record<string, any>;
  request_headers?: Record<string, string>;
  request_body?: any;
  expected_status_code: number;
  expected_response_schema?: Record<string, any>;
  expected_response_contains?: string[];
  is_valid: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestDataResponse {
  id: string;
  endpoint_id: string;
  name: string;
  description: string;
  request_params?: Record<string, any>;
  request_headers?: Record<string, string>;
  request_body?: any;
  expected_status_code: number;
  expected_response_schema?: Record<string, any>;
  expected_response_contains?: string[];
  is_valid: boolean;
  created_at: string;
  updated_at: string;
}

import type { PaginationMetadata } from "./endpoint.types";

export interface TestDataListResponse {
  test_data_items: TestDataResponse[];
  pagination: PaginationMetadata;
  valid_count: number;
  invalid_count: number;
}

export interface GenerateTestDataRequest {
  count: number;
  include_invalid_data: boolean;
  override_existing?: boolean;
}

export interface GenerateTestDataResponse {
  endpoint_id: string;
  endpoint_name: string;
  test_data_items: TestDataResponse[];
  total_count: number;
  valid_count: number;
  invalid_count: number;
  generation_success: boolean;
  deleted_existing_count: number;
  execution_timestamp: string;
}

export interface UpdateTestDataRequest {
  name?: string;
  description?: string;
  request_params?: Record<string, any>;
  request_headers?: Record<string, string>;
  request_body?: any;
  expected_status_code?: number;
  expected_response_schema?: Record<string, any>;
  expected_response_contains?: string[];
  is_valid?: boolean;
}
