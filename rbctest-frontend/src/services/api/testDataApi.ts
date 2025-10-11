import { baseApi } from "./baseApi";
import type {
  TestDataResponse,
  TestDataListResponse,
  GenerateTestDataRequest,
  GenerateTestDataResponse,
  UpdateTestDataRequest,
} from "@/types";

export const testDataApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getAllTestData: builder.query<
      TestDataListResponse,
      { limit?: number; offset?: number }
    >({
      query: ({ limit = 100, offset = 0 }) => ({
        url: `/api/v1/test-data/`,
        params: { limit, offset },
      }),
      providesTags: ["TestData"],
    }),

    getTestDataByEndpointName: builder.query<TestDataListResponse, string>({
      query: (endpointName) =>
        `/api/v1/test-data/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
      providesTags: (_result, _error, endpointName) => [
        { type: "TestData", id: `endpoint-${endpointName}` },
      ],
    }),

    getTestDataByEndpointId: builder.query<TestDataListResponse, string>({
      query: (endpointId) => `/api/v1/test-data/by-endpoint-id/${endpointId}`,
      providesTags: (_result, _error, endpointId) => [
        { type: "TestData", id: `endpoint-id-${endpointId}` },
      ],
    }),

    getTestDataById: builder.query<TestDataResponse, string>({
      query: (id) => `/api/v1/test-data/${id}`,
      providesTags: (_result, _error, id) => [{ type: "TestData", id }],
    }),

    generateTestData: builder.mutation<
      GenerateTestDataResponse,
      { endpointName: string; body: GenerateTestDataRequest }
    >({
      query: ({ endpointName, body }) => ({
        url: `/api/v1/test-data/generate/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { endpointName }) => [
        { type: "TestData", id: `endpoint-${endpointName}` },
      ],
    }),

    updateTestData: builder.mutation<
      TestDataResponse,
      { id: string; body: UpdateTestDataRequest }
    >({
      query: ({ id, body }) => ({
        url: `/api/v1/test-data/${id}`,
        method: "PUT",
        body,
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: "TestData", id }],
    }),

    deleteTestDataByEndpointName: builder.mutation<
      { message: string; deleted_count: number },
      string
    >({
      query: (endpointName) => ({
        url: `/api/v1/test-data/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, endpointName) => [
        { type: "TestData", id: `endpoint-${endpointName}` },
      ],
    }),
  }),
});

export const {
  useGetAllTestDataQuery,
  useGetTestDataByEndpointNameQuery,
  useGetTestDataByEndpointIdQuery,
  useGetTestDataByIdQuery,
  useGenerateTestDataMutation,
  useUpdateTestDataMutation,
  useDeleteTestDataByEndpointNameMutation,
} = testDataApi;
