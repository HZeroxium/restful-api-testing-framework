export interface CleanupResponse {
  message: string;
  endpoint_name: string;
  endpoint_id: string;
  deleted_counts?: {
    executions: number;
    test_data: number;
    validation_scripts: number;
    constraints: number;
  };
  deleted_count?: number;
  total_deleted?: number;
}
