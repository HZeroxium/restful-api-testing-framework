import { baseApi } from "./baseApi";
import type {
  Dataset,
  CreateDatasetRequest,
  CreateDatasetFromFileResponse,
} from "@/types";

export const datasetsApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getDatasets: builder.query<Dataset[], void>({
      query: () => "/api/v1/datasets/",
      providesTags: ["Dataset"],
    }),

    getDataset: builder.query<Dataset, string>({
      query: (id) => `/api/v1/datasets/${id}`,
      providesTags: (_result, _error, id) => [{ type: "Dataset", id }],
    }),

    createDataset: builder.mutation<Dataset, CreateDatasetRequest>({
      query: (body) => ({
        url: "/api/v1/datasets/",
        method: "POST",
        body,
      }),
      invalidatesTags: ["Dataset"],
    }),

    uploadSpec: builder.mutation<CreateDatasetFromFileResponse, FormData>({
      query: (formData) => ({
        url: "/api/v1/datasets/upload-spec",
        method: "POST",
        body: formData,
        // Don't set Content-Type header for FormData
        prepareHeaders: (headers: Headers) => {
          headers.delete("Content-Type");
          return headers;
        },
      }),
      invalidatesTags: ["Dataset"],
    }),

    deleteDataset: builder.mutation<void, string>({
      query: (id) => ({
        url: `/api/v1/datasets/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Dataset"],
    }),

    getDatasetEndpoints: builder.query<any[], string>({
      query: (id) => `/api/v1/datasets/${id}/endpoints`,
      providesTags: (_result, _error, id) => [
        { type: "Endpoint", id: `dataset-${id}` },
      ],
    }),
  }),
});

export const {
  useGetDatasetsQuery,
  useGetDatasetQuery,
  useCreateDatasetMutation,
  useUploadSpecMutation,
  useDeleteDatasetMutation,
  useGetDatasetEndpointsQuery,
} = datasetsApi;
