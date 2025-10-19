import { baseApi } from "./baseApi";

export interface PlaygroundExecuteRequest {
  method: string;
  base_url: string;
  path: string;
  params?: Record<string, any>;
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  retries?: number;
}

export interface PlaygroundExecuteResponse {
  url: string;
  status_code: number;
  headers: Record<string, any>;
  body?: any;
  elapsed_ms: number;
  error?: string | null;
}

export const playgroundApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    execute: builder.mutation<
      PlaygroundExecuteResponse,
      PlaygroundExecuteRequest
    >({
      query: (body) => ({
        url: "/api/v1/playground/execute",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const { useExecuteMutation } = playgroundApi;
