import type { MineConstraintsResponse } from "./constraint.types";
import type { GenerateScriptsResponse } from "./validation-script.types";

export interface ConstraintsScriptsAggregatorResponse {
  endpoint_name: string;
  endpoint_id: string;
  constraints_result: MineConstraintsResponse;
  scripts_result: GenerateScriptsResponse;
  total_constraints: number;
  total_scripts: number;
  total_execution_time: number;
  deleted_constraints_count: number;
  deleted_scripts_count: number;
  constraints_mining_success: boolean;
  scripts_generation_success: boolean;
  overall_success: boolean;
  constraints_error?: string;
  scripts_error?: string;
  execution_timestamp: string;
}

export interface FullPipelineRequest {
  base_url: string;
  test_count: number;
  include_invalid: boolean;
  override_existing: boolean;
}

export interface FullPipelineResponse {
  endpoint_name: string;
  endpoint_id: string;
  constraints_result: MineConstraintsResponse;
  scripts_result: GenerateScriptsResponse;
  test_data_result: any; // TestData generation result
  execution_result: any; // Test execution result
  total_execution_time: number;
  overall_success: boolean;
  step_results: {
    constraints_mining: boolean;
    script_generation: boolean;
    test_data_generation: boolean;
    test_execution: boolean;
  };
  error_message?: string;
  execution_timestamp: string;
}
