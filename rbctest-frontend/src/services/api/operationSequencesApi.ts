import { baseApi } from "./baseApi";
import type {
  OperationSequenceListResponse,
  OperationSequenceResponse,
  GenerateSequencesRequest,
  GenerateSequencesResponse,
  DependencyGraphResponse,
  UpdateSequenceRequest,
  SequenceStatistics,
  SequenceValidation,
} from "@/types";

export const operationSequencesApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    // Generate sequences for a dataset
    generateSequences: builder.mutation<
      GenerateSequencesResponse,
      { datasetId: string; body: GenerateSequencesRequest }
    >({
      query: ({ datasetId, body }) => ({
        url: `/api/v1/operation-sequences/generate/by-dataset-id/${datasetId}`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["OperationSequence"],
    }),

    // Get sequences by dataset
    getSequencesByDataset: builder.query<
      OperationSequenceListResponse,
      { datasetId: string; limit?: number; offset?: number }
    >({
      query: ({ datasetId, limit = 50, offset = 0 }) => ({
        url: `/api/v1/operation-sequences/by-dataset-id/${datasetId}`,
        params: { limit, offset },
      }),
      providesTags: ["OperationSequence"],
    }),

    // Get single sequence
    getSequenceById: builder.query<OperationSequenceResponse, string>({
      query: (sequenceId) => `/api/v1/operation-sequences/${sequenceId}`,
      providesTags: ["OperationSequence"],
    }),

    // Get dependency graph
    getDependencyGraph: builder.query<DependencyGraphResponse, string>({
      query: (datasetId) =>
        `/api/v1/operation-sequences/graph/by-dataset-id/${datasetId}`,
      providesTags: ["OperationSequence"],
    }),

    // Update sequence
    updateSequence: builder.mutation<
      OperationSequenceResponse,
      { sequenceId: string; body: UpdateSequenceRequest }
    >({
      query: ({ sequenceId, body }) => ({
        url: `/api/v1/operation-sequences/${sequenceId}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: ["OperationSequence"],
    }),

    // Delete sequences by dataset
    deleteSequencesByDataset: builder.mutation<
      { deleted_count: number },
      string
    >({
      query: (datasetId) => ({
        url: `/api/v1/operation-sequences/by-dataset-id/${datasetId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["OperationSequence"],
    }),

    // Delete single sequence
    deleteSequence: builder.mutation<void, string>({
      query: (sequenceId) => ({
        url: `/api/v1/operation-sequences/${sequenceId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["OperationSequence"],
    }),

    // Get sequences by type
    getSequencesByType: builder.query<
      OperationSequenceListResponse,
      { sequenceType: string; limit?: number; offset?: number }
    >({
      query: ({ sequenceType, limit = 50, offset = 0 }) => ({
        url: `/api/v1/operation-sequences/type/${sequenceType}`,
        params: { limit, offset },
      }),
      providesTags: ["OperationSequence"],
    }),

    // Get statistics
    getSequenceStatistics: builder.query<SequenceStatistics, void>({
      query: () => `/api/v1/operation-sequences/statistics/overview`,
      providesTags: ["OperationSequence"],
    }),

    // Validate sequence
    validateSequence: builder.mutation<
      SequenceValidation,
      OperationSequenceResponse
    >({
      query: (sequence) => ({
        url: `/api/v1/operation-sequences/validate`,
        method: "POST",
        body: sequence,
      }),
    }),
  }),
});

export const {
  useGenerateSequencesMutation,
  useGetSequencesByDatasetQuery,
  useGetSequenceByIdQuery,
  useGetDependencyGraphQuery,
  useUpdateSequenceMutation,
  useDeleteSequencesByDatasetMutation,
  useDeleteSequenceMutation,
  useGetSequencesByTypeQuery,
  useGetSequenceStatisticsQuery,
  useValidateSequenceMutation,
} = operationSequencesApi;
