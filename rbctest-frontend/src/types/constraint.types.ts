export interface ApiConstraint {
  id: string;
  endpoint_id?: string;
  type: string;
  description: string;
  severity: string;
  source: string;
  details: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ConstraintResponse {
  id: string;
  endpoint_id?: string;
  type: string;
  description: string;
  severity: string;
  source: string;
  details: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface ConstraintCreateRequest {
  endpoint_id: string;
  type: string;
  description: string;
  severity: string;
  source: string;
  details: Record<string, any>;
}

export interface ConstraintListResponse {
  constraints: ConstraintResponse[];
  total: number;
}

export interface MineConstraintsRequest {
  endpoint_id: string;
  override_existing?: boolean;
}

export interface MineConstraintsResponse {
  endpoint_id: string;
  endpoint_method: string;
  endpoint_path: string;
  constraints: ConstraintResponse[];
  request_param_constraints: ConstraintResponse[];
  request_body_constraints: ConstraintResponse[];
  response_property_constraints: ConstraintResponse[];
  request_response_constraints: ConstraintResponse[];
  total_constraints: number;
  result: Record<string, any>;
}

export type ConstraintType =
  | "REQUEST_PARAM"
  | "REQUEST_BODY"
  | "RESPONSE_PROPERTY"
  | "REQUEST_RESPONSE";

export type ConstraintSeverity = "error" | "warning" | "info";
