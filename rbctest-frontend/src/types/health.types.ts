export interface HealthStatus {
  status: string;
  timestamp: string;
  service: string;
  version: string;
}

export interface ServiceHealth {
  status: string;
  error?: string;
  [key: string]: any;
}

export interface ServicesHealthResponse {
  status: string;
  timestamp: string;
  services: Record<string, ServiceHealth>;
  overall_healthy: boolean;
}
