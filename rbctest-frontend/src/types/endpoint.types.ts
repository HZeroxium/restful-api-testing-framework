export interface EndpointInfo {
  id: string;
  name: string;
  description?: string;
  path: string;
  method: string;
  tags: string[];
  auth_required: boolean;
  auth_type?: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface EndpointResponse {
  id: string;
  name: string;
  description?: string;
  path: string;
  method: string;
  tags: string[];
  auth_required: boolean;
  auth_type?: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface EndpointCreateRequest {
  name: string;
  description?: string;
  path: string;
  method: string;
  tags: string[];
  auth_required: boolean;
  auth_type?: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
}

export interface EndpointUpdateRequest {
  name?: string;
  description?: string;
  path?: string;
  method?: string;
  tags?: string[];
  auth_required?: boolean;
  auth_type?: string;
  input_schema?: Record<string, any>;
  output_schema?: Record<string, any>;
}

export interface EndpointListResponse {
  endpoints: EndpointResponse[];
  total: number;
  page: number;
  size: number;
}

export interface ParseSpecRequest {
  spec_source: string;
  source_type: "file" | "url" | "content";
  filter_tags?: string[];
  filter_paths?: string[];
  filter_methods?: string[];
}

export interface ParseSpecResponse {
  success: boolean;
  message: string;
  api_title?: string;
  api_version?: string;
  total_endpoints: number;
  created_endpoints: number;
  skipped_endpoints: number;
  endpoints: EndpointResponse[];
}

export interface EndpointStatsResponse {
  total_endpoints: number;
  method_distribution: Record<string, number>;
  auth_type_distribution: Record<string, number>;
  tag_distribution: Record<string, number>;
  last_updated: string;
}

export interface SearchEndpointsRequest {
  tag?: string;
  path_pattern?: string;
  method?: string;
  auth_required?: boolean;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  timestamp: string;
}
