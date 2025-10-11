import { baseApi } from "./baseApi";
import type {
  ConstraintsScriptsAggregatorResponse,
  FullPipelineRequest,
  FullPipelineResponse,
} from "@/types";

export const aggregatorApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    mineConstraintsAndGenerateScripts: builder.mutation<
      ConstraintsScriptsAggregatorResponse,
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/aggregator/constraints-scripts/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
      }),
      invalidatesTags: ["Constraint", "ValidationScript"],
    }),

    runFullPipeline: builder.mutation<
      FullPipelineResponse,
      { endpointName: string; body: FullPipelineRequest }
    >({
      query: ({ endpointName, body }) => ({
        url: `/api/v1/aggregator/full-pipeline/${encodeURIComponent(
          endpointName
        )}`,
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
  }),
});

export const {
  useMineConstraintsAndGenerateScriptsMutation,
  useRunFullPipelineMutation,
} = aggregatorApi;
