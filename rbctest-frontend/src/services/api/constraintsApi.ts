import { baseApi } from "./baseApi";
import type {
  ConstraintResponse,
  ConstraintListResponse,
  ConstraintCreateRequest,
  MineConstraintsRequest,
  MineConstraintsResponse,
} from "@/types";

export const constraintsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getConstraints: builder.query<
      ConstraintListResponse,
      { endpoint_id?: string }
    >({
      query: ({ endpoint_id }) => ({
        url: "/api/v1/constraints/",
        params: endpoint_id ? { endpoint_id } : {},
      }),
      providesTags: ["Constraint"],
    }),

    getConstraint: builder.query<ConstraintResponse, string>({
      query: (id) => `/api/v1/constraints/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Constraint", id }],
    }),

    getConstraintsByEndpointName: builder.query<ConstraintListResponse, string>(
      {
        query: (endpointName) =>
          `/api/v1/constraints/by-endpoint-name/${encodeURIComponent(
            endpointName
          )}`,
        providesTags: (_result, _error, endpointName) => [
          { type: "Constraint", id: `endpoint-${endpointName}` },
        ],
      }
    ),

    getConstraintsByEndpointId: builder.query<ConstraintListResponse, string>({
      query: (endpointId) => `/api/v1/constraints/by-endpoint-id/${endpointId}`,
      providesTags: (_result, _error, endpointId) => [
        { type: "Constraint", id: `endpoint-id-${endpointId}` },
      ],
    }),

    createConstraint: builder.mutation<
      ConstraintResponse,
      ConstraintCreateRequest
    >({
      query: (body) => ({
        url: "/api/v1/constraints/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Constraint"],
    }),

    mineConstraints: builder.mutation<
      MineConstraintsResponse,
      MineConstraintsRequest
    >({
      query: (body) => ({
        url: "/api/v1/constraints/mine",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Constraint"],
    }),

    mineConstraintsByEndpointName: builder.mutation<
      MineConstraintsResponse,
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/constraints/mine/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
      }),
      invalidatesTags: ["Constraint"],
    }),

    deleteConstraint: builder.mutation<void, string>({
      query: (id) => ({
        url: `/api/v1/constraints/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Constraint"],
    }),

    deleteConstraintsByEndpointName: builder.mutation<
      { message: string; deleted_count: number },
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/constraints/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Constraint"],
    }),
  }),
});

export const {
  useGetConstraintsQuery,
  useGetConstraintQuery,
  useGetConstraintsByEndpointNameQuery,
  useGetConstraintsByEndpointIdQuery,
  useCreateConstraintMutation,
  useMineConstraintsMutation,
  useMineConstraintsByEndpointNameMutation,
  useDeleteConstraintMutation,
  useDeleteConstraintsByEndpointNameMutation,
} = constraintsApi;
