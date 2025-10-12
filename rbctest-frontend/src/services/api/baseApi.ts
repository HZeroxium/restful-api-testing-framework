import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

// Get API base URL from environment variable
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
    prepareHeaders: (headers) => {
      // Add any default headers here if needed
      headers.set("Content-Type", "application/json");
      return headers;
    },
  }),
  tagTypes: [
    "Dataset",
    "Endpoint",
    "Constraint",
    "ValidationScript",
    "TestData",
    "Execution",
    "Verification",
    "Health",
  ],
  endpoints: () => ({}),
});

export default baseApi;
