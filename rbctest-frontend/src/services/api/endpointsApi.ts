import { baseApi } from "./baseApi";
import type {
  EndpointResponse,
  EndpointListResponse,
  EndpointCreateRequest,
  EndpointUpdateRequest,
  ParseSpecRequest,
  ParseSpecResponse,
  EndpointStatsResponse,
} from "@/types";

export const endpointsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getEndpoints: builder.query<
      EndpointListResponse,
      { limit?: number; offset?: number }
    >({
      query: ({ limit = 10, offset = 0 }) => ({
        url: "/api/v1/endpoints/",
        params: { limit, offset },
      }),
      providesTags: ["Endpoint"],
    }),

    getEndpoint: builder.query<EndpointResponse, string>({
      query: (id) => `/api/v1/endpoints/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Endpoint", id }],
    }),

    getEndpointByName: builder.query<EndpointResponse, string>({
      query: (name) =>
        `/api/v1/endpoints/by-endpoint-name/${encodeURIComponent(name)}`,
      providesTags: (_result, _error, name) => [
        { type: "Endpoint", id: `name-${name}` },
      ],
    }),

    createEndpoint: builder.mutation<EndpointResponse, EndpointCreateRequest>({
      query: (body) => ({
        url: "/api/v1/endpoints/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Endpoint"],
    }),

    updateEndpoint: builder.mutation<
      EndpointResponse,
      { id: string; body: EndpointUpdateRequest }
    >({
      query: ({ id, body }) => ({
        url: `/api/v1/endpoints/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: "Endpoint", id }],
    }),

    deleteEndpoint: builder.mutation<void, string>({
      query: (id) => ({
        url: `/api/v1/endpoints/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Endpoint"],
    }),

    searchByTag: builder.query<EndpointListResponse, string>({
      query: (tag) => `/api/v1/endpoints/search/tag/${encodeURIComponent(tag)}`,
      providesTags: ["Endpoint"],
    }),

    searchByPath: builder.query<EndpointListResponse, string>({
      query: (pattern) =>
        `/api/v1/endpoints/search/path?pattern=${encodeURIComponent(pattern)}`,
      providesTags: ["Endpoint"],
    }),

    parseSpec: builder.mutation<ParseSpecResponse, ParseSpecRequest>({
      query: (body) => ({
        url: "/api/v1/endpoints/parse-spec",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Endpoint"],
    }),

    getEndpointStats: builder.query<EndpointStatsResponse, void>({
      query: () => "/api/v1/endpoints/stats",
      providesTags: ["Endpoint"],
    }),

    exportEndpoints: builder.query<any, void>({
      query: () => "/api/v1/endpoints/export/json",
      providesTags: ["Endpoint"],
    }),
  }),
});

export const {
  useGetEndpointsQuery,
  useGetEndpointQuery,
  useGetEndpointByNameQuery,
  useCreateEndpointMutation,
  useUpdateEndpointMutation,
  useDeleteEndpointMutation,
  useSearchByTagQuery,
  useSearchByPathQuery,
  useParseSpecMutation,
  useGetEndpointStatsQuery,
  useLazyExportEndpointsQuery,
} = endpointsApi;
