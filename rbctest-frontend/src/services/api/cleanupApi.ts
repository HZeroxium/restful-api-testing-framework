import { baseApi } from "./baseApi";
import type { CleanupResponse } from "@/types";

export const cleanupApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    cleanupEndpointArtifacts: builder.mutation<CleanupResponse, string>({
      query: (endpointName) => ({
        url: `/api/v1/cleanup/endpoint/${encodeURIComponent(endpointName)}`,
        method: "DELETE",
      }),
      invalidatesTags: [
        "Constraint",
        "ValidationScript",
        "TestData",
        "Execution",
      ],
    }),

    cleanupEndpointConstraints: builder.mutation<CleanupResponse, string>({
      query: (endpointName) => ({
        url: `/api/v1/cleanup/endpoint/${encodeURIComponent(
          endpointName
        )}/constraints`,
        method: "DELETE",
      }),
      invalidatesTags: ["Constraint", "ValidationScript"],
    }),

    cleanupEndpointTestData: builder.mutation<CleanupResponse, string>({
      query: (endpointName) => ({
        url: `/api/v1/cleanup/endpoint/${encodeURIComponent(
          endpointName
        )}/test-data`,
        method: "DELETE",
      }),
      invalidatesTags: ["TestData"],
    }),

    cleanupEndpointExecutions: builder.mutation<CleanupResponse, string>({
      query: (endpointName) => ({
        url: `/api/v1/cleanup/endpoint/${encodeURIComponent(
          endpointName
        )}/executions`,
        method: "DELETE",
      }),
      invalidatesTags: ["Execution"],
    }),
  }),
});

export const {
  useCleanupEndpointArtifactsMutation,
  useCleanupEndpointConstraintsMutation,
  useCleanupEndpointTestDataMutation,
  useCleanupEndpointExecutionsMutation,
} = cleanupApi;
