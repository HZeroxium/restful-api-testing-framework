export interface BatchResult {
  endpoint_name: string;
  success: boolean;
  error_message?: string;
  execution_time_ms: number;
  details: Record<string, any>;
}

export interface BatchResponse {
  total_endpoints: number;
  successful_endpoints: number;
  failed_endpoints: number;
  success_rate: number;
  total_execution_time_ms: number;
  results: BatchResult[];
}

export interface BatchConstraintMiningRequest {
  endpoint_names: string[];
  base_url: string;
  use_mock_api: boolean;
}

export interface BatchValidationScriptGenerationRequest {
  endpoint_names: string[];
  base_url: string;
  use_mock_api: boolean;
}

export interface BatchFullPipelineRequest {
  endpoint_names: string[];
  base_url: string;
  use_mock_api: boolean;
}
