import type { PaginationMetadata } from "./endpoint.types";

export interface OperationDependency {
  source_operation: string;
  target_operation: string;
  reason: string;
  data_mapping: Record<string, any>;
}

export interface OperationNode {
  id: string;
  operation: string;
  method: string;
  path: string;
  endpoint_id?: string;
  metadata: Record<string, any>;
}

export interface DependencyEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  dependency_type: "path_param" | "response_field" | "workflow";
  reason: string;
  data_mapping: Record<string, any>;
  confidence: number;
}

export interface DependencyGraph {
  nodes: OperationNode[];
  edges: DependencyEdge[];
  metadata: Record<string, any>;
}

export interface OperationSequenceResponse {
  id: string;
  name: string;
  description: string;
  operations: string[];
  dependencies: OperationDependency[];
  sequence_type: string;
  priority: number;
  estimated_duration?: number;
  metadata: Record<string, any>;
}

export interface OperationSequenceListResponse {
  sequences: OperationSequenceResponse[];
  pagination: PaginationMetadata;
}

export interface GenerateSequencesRequest {
  override_existing: boolean;
}

export interface GenerateSequencesResponse {
  dataset_id: string;
  total_endpoints: number;
  sequences_generated: number;
  analysis_method: string;
  graph?: Record<string, any>;
  sequences: OperationSequenceResponse[];
  result: Record<string, any>;
}

export interface DependencyGraphResponse {
  nodes: OperationNode[];
  edges: DependencyEdge[];
  metadata: Record<string, any>;
}

export interface UpdateSequenceRequest {
  name?: string;
  description?: string;
  operations?: string[];
  sequence_type?: string;
  priority?: number;
  estimated_duration?: number | undefined;
  metadata?: Record<string, any>;
}

export interface SequenceStatistics {
  total_sequences: number;
  sequences_by_type: Record<string, number>;
  sequences_with_dependencies: number;
  average_operations_per_sequence: number;
  sequences_by_priority: Record<number, number>;
}

export interface SequenceValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
}
