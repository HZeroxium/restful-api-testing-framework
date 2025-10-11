// Re-export all types for easy importing
export * from "./dataset.types";
export * from "./endpoint.types";
export * from "./constraint.types";
export * from "./validation-script.types";
export * from "./test-data.types";
export * from "./execution.types";
export * from "./verification.types";
export * from "./aggregator.types";

// Common types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T = any> {
  data: T[];
  total: number;
  page: number;
  size: number;
  totalPages: number;
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface FilterOption {
  key: string;
  label: string;
  type: "text" | "select" | "multiselect" | "date" | "number";
  options?: SelectOption[];
}

export interface TableColumn<T = any> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  width?: string | number;
  align?: "left" | "center" | "right";
  render?: (value: any, row: T) => React.ReactNode;
}

export interface SortConfig {
  key: string;
  direction: "asc" | "desc";
}

export interface FilterConfig {
  [key: string]: any;
}

export interface LoadingState {
  isLoading: boolean;
  error?: string;
  data?: any;
}
