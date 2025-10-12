import { baseApi } from "./baseApi";
import type { HealthStatus, ServicesHealthResponse } from "@/types";

export const healthApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getHealthStatus: builder.query<HealthStatus, void>({
      query: () => `/api/v1/health/`,
    }),

    getServicesHealth: builder.query<ServicesHealthResponse, void>({
      query: () => `/api/v1/health/services`,
    }),

    getHealthReady: builder.query<any, void>({
      query: () => `/api/v1/health/ready`,
    }),

    getHealthLive: builder.query<any, void>({
      query: () => `/api/v1/health/live`,
    }),
  }),
});

export const {
  useGetHealthStatusQuery,
  useGetServicesHealthQuery,
  useGetHealthReadyQuery,
  useGetHealthLiveQuery,
} = healthApi;
