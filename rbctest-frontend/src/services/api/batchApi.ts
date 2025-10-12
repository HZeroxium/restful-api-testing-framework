import { baseApi } from "./baseApi";
import type {
  BatchConstraintMiningRequest,
  BatchValidationScriptGenerationRequest,
  BatchFullPipelineRequest,
  BatchResponse,
} from "@/types";

export const batchApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    batchMineConstraints: builder.mutation<
      BatchResponse,
      BatchConstraintMiningRequest
    >({
      query: (body) => ({
        url: `/api/v1/batch/constraints/mine`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["Constraint"],
    }),

    batchGenerateValidationScripts: builder.mutation<
      BatchResponse,
      BatchValidationScriptGenerationRequest
    >({
      query: (body) => ({
        url: `/api/v1/batch/validation-scripts/generate`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    batchRunFullPipeline: builder.mutation<
      BatchResponse,
      BatchFullPipelineRequest
    >({
      query: (body) => ({
        url: `/api/v1/batch/full-pipeline`,
        method: "POST",
        body,
      }),
      invalidatesTags: [
        "Constraint",
        "ValidationScript",
        "TestData",
        "Execution",
      ],
    }),

    getAvailableEndpointsForBatch: builder.query<
      { total_endpoints: number; endpoints: any[] },
      void
    >({
      query: () => `/api/v1/batch/endpoints/available`,
      providesTags: ["Endpoint"],
    }),
  }),
});

export const {
  useBatchMineConstraintsMutation,
  useBatchGenerateValidationScriptsMutation,
  useBatchRunFullPipelineMutation,
  useGetAvailableEndpointsForBatchQuery,
} = batchApi;
