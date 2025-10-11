import { baseApi } from "./baseApi";
import type {
  VerifyTestDataRequest,
  VerifyTestDataResponse,
  VerifyRequestResponseRequest,
  VerifyRequestResponseResponse,
} from "@/types";

export const verificationApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    verifyTestData: builder.mutation<
      VerifyTestDataResponse,
      { endpointName: string; body: VerifyTestDataRequest }
    >({
      query: ({ endpointName, body }) => ({
        url: `/api/v1/verify/test-data/by-endpoint-name/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
        body,
      }),
    }),

    verifyRequestResponse: builder.mutation<
      VerifyRequestResponseResponse,
      { endpointName: string; body: VerifyRequestResponseRequest }
    >({
      query: ({ endpointName, body }) => ({
        url: `/api/v1/verify/request-response/${encodeURIComponent(
          endpointName
        )}`,
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useVerifyTestDataMutation, useVerifyRequestResponseMutation } =
  verificationApi;
