import { baseApi } from "./baseApi";
import type {
  ExecuteTestRequest,
  ExecuteTestResponse,
  ExecutionHistoryListResponse,
  ExecutionDetailResponse,
} from "@/types";

export const executionApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllExecutions: builder.query<
      ExecutionHistoryListResponse,
      { limit?: number; offset?: number }
    >({
      query: ({ limit = 50, offset = 0 }) => ({
        url: `/api/v1/execute/history/`,
        params: { limit, offset },
      }),
      providesTags: ["Execution"],
    }),

    executeTestsByEndpointName: builder.mutation<
      ExecuteTestResponse,
      { endpointName: string; body: ExecuteTestRequest }
    >({
      query: ({ endpointName, body }) => ({
        url: `/api/v1/execute/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["Execution"],
    }),

    executeTestsByEndpointId: builder.mutation<
      ExecuteTestResponse,
      { endpointId: string; body: ExecuteTestRequest }
    >({
      query: ({ endpointId, body }) => ({
        url: `/api/v1/execute/by-endpoint-id/${endpointId}`,
        method: "POST",
        body,
      }),
      invalidatesTags: ["Execution"],
    }),

    getExecutionHistoryByEndpointName: builder.query<
      ExecutionHistoryListResponse,
      { endpointName: string; limit?: number }
    >({
      query: ({ endpointName, limit = 10 }) =>
        `/api/v1/execute/history/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}?limit=${limit}`,
      providesTags: (_result, _error, { endpointName }) => [
        { type: "Execution", id: `history-${endpointName}` },
      ],
    }),

    getExecutionHistoryByEndpointId: builder.query<
      ExecutionHistoryListResponse,
      { endpointId: string; limit?: number }
    >({
      query: ({ endpointId, limit = 10 }) =>
        `/api/v1/execute/history/by-endpoint-id/${endpointId}?limit=${limit}`,
      providesTags: (_result, _error, { endpointId }) => [
        { type: "Execution", id: `history-id-${endpointId}` },
      ],
    }),

    getExecutionDetails: builder.query<ExecutionDetailResponse, string>({
      query: (executionId) => `/api/v1/execute/history/${executionId}`,
      providesTags: (_result, _error, executionId) => [
        { type: "Execution", id: executionId },
      ],
    }),

    deleteExecution: builder.mutation<{ message: string }, string>({
      query: (executionId) => ({
        url: `/api/v1/execute/history/${executionId}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, executionId) => [
        { type: "Execution", id: executionId },
      ],
    }),
  }),
});

export const {
  useGetAllExecutionsQuery,
  useExecuteTestsByEndpointNameMutation,
  useExecuteTestsByEndpointIdMutation,
  useGetExecutionHistoryByEndpointNameQuery,
  useGetExecutionHistoryByEndpointIdQuery,
  useGetExecutionDetailsQuery,
  useDeleteExecutionMutation,
} = executionApi;
