export interface ValidationScript {
  id: string;
  endpoint_id?: string;
  name: string;
  script_type: string;
  validation_code: string;
  description: string;
  constraint_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ValidationScriptResponse {
  id: string;
  endpoint_id?: string;
  name: string;
  script_type: string;
  validation_code: string;
  description: string;
  constraint_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ValidationScriptCreateRequest {
  endpoint_id: string;
  name: string;
  script_type: string;
  validation_code: string;
  description: string;
  constraint_id?: string;
}

import type { PaginationMetadata } from "./endpoint.types";

export interface ValidationScriptListResponse {
  scripts: ValidationScriptResponse[];
  pagination: PaginationMetadata;
}

export interface GenerateScriptsRequest {
  endpoint_id: string;
  override_existing?: boolean;
}

export interface GenerateScriptsResponse {
  endpoint_id: string;
  scripts: ValidationScriptResponse[];
  total_scripts: number;
}

export type ScriptType =
  | "REQUEST_PARAM"
  | "REQUEST_BODY"
  | "RESPONSE_PROPERTY"
  | "REQUEST_RESPONSE";
