import { baseApi } from "./baseApi";
import type {
  ValidationScriptResponse,
  ValidationScriptListResponse,
  ValidationScriptCreateRequest,
  GenerateScriptsRequest,
  GenerateScriptsResponse,
} from "@/types";

export const validationScriptsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getScripts: builder.query<
      ValidationScriptListResponse,
      { endpoint_id?: string }
    >({
      query: ({ endpoint_id }) => ({
        url: "/api/v1/validation-scripts/",
        params: endpoint_id ? { endpoint_id } : {},
      }),
      providesTags: ["ValidationScript"],
    }),

    getScript: builder.query<ValidationScriptResponse, string>({
      query: (id) => `/api/v1/validation-scripts/${id}`,
      providesTags: (_result, _error, id) => [{ type: "ValidationScript", id }],
    }),

    getScriptsByEndpointName: builder.query<
      ValidationScriptListResponse,
      string
    >({
      query: (endpointName) =>
        `/api/v1/validation-scripts/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
      providesTags: (_result, _error, endpointName) => [
        { type: "ValidationScript", id: `endpoint-${endpointName}` },
      ],
    }),

    getScriptsByEndpointId: builder.query<ValidationScriptListResponse, string>(
      {
        query: (endpointId) =>
          `/api/v1/validation-scripts/by-endpoint-id/${endpointId}`,
        providesTags: (_result, _error, endpointId) => [
          { type: "ValidationScript", id: `endpoint-id-${endpointId}` },
        ],
      }
    ),

    createScript: builder.mutation<
      ValidationScriptResponse,
      ValidationScriptCreateRequest
    >({
      query: (body) => ({
        url: "/api/v1/validation-scripts/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    generateScripts: builder.mutation<
      GenerateScriptsResponse,
      GenerateScriptsRequest
    >({
      query: (body) => ({
        url: "/api/v1/validation-scripts/generate",
        method: "POST",
        body,
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    generateScriptsByEndpointName: builder.mutation<
      GenerateScriptsResponse,
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/validation-scripts/generate/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    deleteScript: builder.mutation<void, string>({
      query: (id) => ({
        url: `/api/v1/validation-scripts/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    deleteScriptsByEndpointName: builder.mutation<
      { message: string; deleted_count: number },
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/validation-scripts/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "DELETE",
      }),
      invalidatesTags: ["ValidationScript"],
    }),

    exportToPythonFile: builder.mutation<
      { message: string; file_content: string },
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/validation-scripts/to-python-file/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
      }),
    }),
  }),
});

export const {
  useGetScriptsQuery,
  useGetScriptQuery,
  useGetScriptsByEndpointNameQuery,
  useGetScriptsByEndpointIdQuery,
  useCreateScriptMutation,
  useGenerateScriptsMutation,
  useGenerateScriptsByEndpointNameMutation,
  useDeleteScriptMutation,
  useDeleteScriptsByEndpointNameMutation,
  useExportToPythonFileMutation,
} = validationScriptsApi;
