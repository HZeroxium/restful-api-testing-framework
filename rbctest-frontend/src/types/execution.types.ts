export interface ExecutionHistory {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  base_url: string;
  overall_status: ExecutionStatus;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  success_rate: number;
  total_execution_time_ms: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  test_data_used: string[];
  execution_results: TestCaseExecutionResult[];
  metadata?: Record<string, any>;
}

export interface ExecutionHistoryResponse {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  base_url: string;
  overall_status: ExecutionStatus;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  success_rate: number;
  total_execution_time_ms: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  test_data_used: string[];
  metadata?: Record<string, any>;
}

export interface TestCaseExecutionResult {
  test_data_id: string;
  test_data_name: string;
  request_sent: Record<string, any>;
  response_received: Record<string, any>;
  execution_status: ExecutionStatus;
  validation_results: Record<string, any>[];
  execution_time_ms: number;
  error_message?: string;
  passed: boolean;
}

export interface TestCaseExecutionResultResponse {
  test_data_id: string;
  test_data_name: string;
  request_sent: Record<string, any>;
  response_received: Record<string, any>;
  execution_status: ExecutionStatus;
  validation_results: Record<string, any>[];
  execution_time_ms: number;
  error_message?: string;
  passed: boolean;
}

export interface ExecuteTestRequest {
  base_url: string;
  test_data_ids?: string[];
  timeout?: number;
  headers?: Record<string, string>;
}

export interface ExecuteTestResponse {
  execution_id: string;
  endpoint_id: string;
  endpoint_name: string;
  base_url: string;
  overall_status: ExecutionStatus;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  success_rate: number;
  total_execution_time_ms: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  execution_results: TestCaseExecutionResultResponse[];
}

export interface ExecutionHistoryListResponse {
  executions: ExecutionHistoryResponse[];
  total_count: number;
}

export interface ExecutionDetailResponse {
  id: string;
  endpoint_id: string;
  endpoint_name: string;
  base_url: string;
  overall_status: ExecutionStatus;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  success_rate: number;
  total_execution_time_ms: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  test_data_used: string[];
  execution_results: TestCaseExecutionResultResponse[];
  metadata?: Record<string, any>;
}

export type ExecutionStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";
