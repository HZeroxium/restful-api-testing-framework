export interface Dataset {
  id: string;
  name: string;
  description?: string;
  spec_version?: string;
  base_url?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDatasetRequest {
  name: string;
  description?: string;
}

export interface CreateDatasetFromFileResponse {
  dataset_id: string;
  dataset_name: string;
  spec_version?: string;
  base_url?: string;
  endpoints_count: number;
  api_title: string;
}

export interface DatasetStats {
  total_datasets: number;
  total_endpoints: number;
  last_updated: string;
}
