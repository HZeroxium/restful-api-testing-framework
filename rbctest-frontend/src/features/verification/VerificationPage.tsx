import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  Tabs,
  Tab,
  Divider,
  Alert,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  LinearProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
} from "@mui/material";

import Grid from "@mui/material/Grid";

import {
  ExpandMore,
  CheckCircle,
  Error as ErrorIcon,
  PlayArrow,
  Add as AddIcon,
  Delete as DeleteIcon,
} from "@mui/icons-material";
import {
  useVerifyTestDataMutation,
  useVerifyRequestResponseMutation,
} from "@/services/api";
import { CodeViewer } from "@/components/common/CodeViewer";
import EndpointAutocomplete from "@/components/common/EndpointAutocomplete";
import type { TestDataItem, RequestResponsePair } from "@/types";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

interface TestDataItemForm {
  id: string;
  method?: string;
  path?: string;
  params: string;
  headers: string;
  body: string;
  expectedStatus: number;
  timeout: number;
}

interface RequestResponseForm {
  id: string;
  method?: string;
  path?: string;
  params: string;
  headers: string;
  body: string;
  expectedStatus: number;
  responseHeaders: string;
  responseBody: string;
  timeout: number;
}

const VerificationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedEndpointName, setSelectedEndpointName] = useState("");
  const [selectedEndpoint, setSelectedEndpoint] = useState<any>(null);

  // Test Data Verification
  const [testDataItems, setTestDataItems] = useState<TestDataItemForm[]>([
    {
      id: "1",
      params: "{}",
      headers: "{}",
      body: "{}",
      expectedStatus: 200,
      timeout: 30,
    },
  ]);

  const [
    verifyTestData,
    {
      isLoading: isVerifyingTestData,
      data: testDataResult,
      error: testDataError,
    },
  ] = useVerifyTestDataMutation();

  // Request-Response Verification
  const [requestResponseItems, setRequestResponseItems] = useState<
    RequestResponseForm[]
  >([
    {
      id: "1",
      params: "{}",
      headers: "{}",
      body: "{}",
      expectedStatus: 200,
      responseHeaders: "{}",
      responseBody: "{}",
      timeout: 30,
    },
  ]);

  const [
    verifyRequestResponse,
    {
      isLoading: isVerifyingRequestResponse,
      data: requestResponseResult,
      error: requestResponseError,
    },
  ] = useVerifyRequestResponseMutation();

  const [expandedTestDataResult, setExpandedTestDataResult] = useState<
    string | false
  >(false);
  const [expandedRequestResponseResult, setExpandedRequestResponseResult] =
    useState<string | false>(false);

  // Load endpoint data when selected
  useEffect(() => {
    if (selectedEndpoint) {
      // Update all items with endpoint defaults
      setTestDataItems((prev) =>
        prev.map((item) => ({
          ...item,
          method: selectedEndpoint.method,
          path: selectedEndpoint.path,
        }))
      );
      setRequestResponseItems((prev) =>
        prev.map((item) => ({
          ...item,
          method: selectedEndpoint.method,
          path: selectedEndpoint.path,
        }))
      );
    }
  }, [selectedEndpoint]);

  const parseJson = (text: string) => {
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      return {};
    }
  };

  const handleVerifyTestData = async () => {
    if (!selectedEndpointName) return;

    try {
      const testDataItemsFormatted: TestDataItem[] = testDataItems.map(
        (item) => ({
          request_params: parseJson(item.params),
          request_headers: parseJson(item.headers),
          request_body: parseJson(item.body),
          expected_status_code: item.expectedStatus,
          method: item.method,
          path: item.path,
          timeout: item.timeout,
        })
      );

      await verifyTestData({
        endpointName: selectedEndpointName,
        body: {
          test_data_items: testDataItemsFormatted,
        },
      }).unwrap();
    } catch (err) {
      console.error("Failed to verify test data:", err);
    }
  };

  const handleVerifyRequestResponse = async () => {
    if (!selectedEndpointName) return;

    try {
      const pairs: RequestResponsePair[] = requestResponseItems.map((item) => ({
        request: {
          method: item.method || "GET",
          url: `${selectedEndpoint?.baseUrl || ""}${item.path || ""}`,
          params: parseJson(item.params),
          headers: parseJson(item.headers),
          body: parseJson(item.body),
        },
        response: {
          status_code: item.expectedStatus,
          headers: parseJson(item.responseHeaders),
          body: parseJson(item.responseBody),
        },
      }));

      await verifyRequestResponse({
        endpointName: selectedEndpointName,
        body: {
          request_response_pairs: pairs,
        },
      }).unwrap();
    } catch (err) {
      console.error("Failed to verify request-response:", err);
    }
  };

  const addTestDataItem = () => {
    const newItem: TestDataItemForm = {
      id: Date.now().toString(),
      method: selectedEndpoint?.method,
      path: selectedEndpoint?.path,
      params: "{}",
      headers: "{}",
      body: "{}",
      expectedStatus: 200,
      timeout: 30,
    };
    setTestDataItems((prev) => [...prev, newItem]);
  };

  const removeTestDataItem = (id: string) => {
    setTestDataItems((prev) => prev.filter((item) => item.id !== id));
  };

  const updateTestDataItem = (
    id: string,
    field: keyof TestDataItemForm,
    value: any
  ) => {
    setTestDataItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const addRequestResponseItem = () => {
    const newItem: RequestResponseForm = {
      id: Date.now().toString(),
      method: selectedEndpoint?.method,
      path: selectedEndpoint?.path,
      params: "{}",
      headers: "{}",
      body: "{}",
      expectedStatus: 200,
      responseHeaders: "{}",
      responseBody: "{}",
      timeout: 30,
    };
    setRequestResponseItems((prev) => [...prev, newItem]);
  };

  const removeRequestResponseItem = (id: string) => {
    setRequestResponseItems((prev) => prev.filter((item) => item.id !== id));
  };

  const updateRequestResponseItem = (
    id: string,
    field: keyof RequestResponseForm,
    value: any
  ) => {
    setRequestResponseItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, [field]: value } : item))
    );
  };

  const handleTestDataAccordionChange =
    (index: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedTestDataResult(isExpanded ? index : false);
    };

  const handleRequestResponseAccordionChange =
    (index: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedRequestResponseResult(isExpanded ? index : false);
    };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
          Verification
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Verify test data and request-response pairs against validation scripts
        </Typography>
      </Box>

      {/* Tabs */}
      <Card>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab label="Test Data Verification" />
          <Tab label="Request-Response Verification" />
        </Tabs>

        <Divider />

        {/* Test Data Verification Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Verify test data items against validation scripts for an endpoint.
              Provide test data in a structured format.
            </Typography>

            <EndpointAutocomplete
              value={selectedEndpointName}
              onChange={(value) => {
                const endpointName = Array.isArray(value)
                  ? value[0] || ""
                  : value;
                setSelectedEndpointName(endpointName);
                // You would typically fetch endpoint details here
                setSelectedEndpoint({
                  method: "GET",
                  path: "/api/example",
                  baseUrl: "https://api.example.com",
                });
              }}
              label="Select Endpoint"
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Test Data Items
              </Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={addTestDataItem}
              >
                Add Item
              </Button>
            </Box>

            {testDataItems.map((item, index) => (
              <Card key={item.id} variant="outlined" sx={{ p: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 2,
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Test Data Item {index + 1}
                  </Typography>
                  <Box>
                    <IconButton
                      size="small"
                      onClick={() => removeTestDataItem(item.id)}
                      disabled={testDataItems.length === 1}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>

                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <FormControl fullWidth>
                      <InputLabel>Method</InputLabel>
                      <Select
                        value={item.method || ""}
                        onChange={(e) =>
                          updateTestDataItem(item.id, "method", e.target.value)
                        }
                      >
                        <MenuItem value="GET">GET</MenuItem>
                        <MenuItem value="POST">POST</MenuItem>
                        <MenuItem value="PUT">PUT</MenuItem>
                        <MenuItem value="PATCH">PATCH</MenuItem>
                        <MenuItem value="DELETE">DELETE</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, md: 9 }}>
                    <TextField
                      label="Path"
                      value={item.path || ""}
                      onChange={(e) =>
                        updateTestDataItem(item.id, "path", e.target.value)
                      }
                      fullWidth
                      placeholder="/api/users"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Query Parameters (JSON)"
                      value={item.params}
                      onChange={(e) =>
                        updateTestDataItem(item.id, "params", e.target.value)
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"page": 1, "limit": 10}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Headers (JSON)"
                      value={item.headers}
                      onChange={(e) =>
                        updateTestDataItem(item.id, "headers", e.target.value)
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"Content-Type": "application/json"}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12 }}>
                    <TextField
                      label="Request Body (JSON)"
                      value={item.body}
                      onChange={(e) =>
                        updateTestDataItem(item.id, "body", e.target.value)
                      }
                      multiline
                      rows={4}
                      fullWidth
                      placeholder='{"name": "John Doe", "email": "john@example.com"}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Expected Status Code"
                      type="number"
                      value={item.expectedStatus}
                      onChange={(e) =>
                        updateTestDataItem(
                          item.id,
                          "expectedStatus",
                          Number(e.target.value)
                        )
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Timeout (seconds)"
                      type="number"
                      value={item.timeout}
                      onChange={(e) =>
                        updateTestDataItem(
                          item.id,
                          "timeout",
                          Number(e.target.value)
                        )
                      }
                      fullWidth
                    />
                  </Grid>
                </Grid>
              </Card>
            ))}

            {testDataError && (
              <Alert severity="error">
                Failed to verify test data. Please check your input and try
                again.
              </Alert>
            )}

            {isVerifyingTestData && (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Verifying test data...
                </Typography>
                <LinearProgress />
              </Box>
            )}

            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleVerifyTestData}
              disabled={!selectedEndpointName || isVerifyingTestData}
              size="large"
            >
              {isVerifyingTestData ? "Verifying..." : "Verify Test Data"}
            </Button>

            {/* Test Data Results */}
            {testDataResult && (
              <Box>
                <Divider sx={{ my: 3 }} />
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Verification Results
                </Typography>

                <Alert
                  severity={testDataResult.overall_passed ? "success" : "error"}
                  icon={
                    testDataResult.overall_passed ? (
                      <CheckCircle />
                    ) : (
                      <ErrorIcon />
                    )
                  }
                  sx={{ mb: 2 }}
                >
                  {testDataResult.overall_passed
                    ? `All ${testDataResult.total_test_data_items} test data items passed verification`
                    : `Some test data items failed verification`}
                </Alert>

                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {testDataResult.verification_results.map((result, index) => (
                    <Accordion
                      key={index}
                      expanded={expandedTestDataResult === `test-${index}`}
                      onChange={handleTestDataAccordionChange(`test-${index}`)}
                    >
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 2,
                            flexGrow: 1,
                          }}
                        >
                          {result.overall_passed ? (
                            <CheckCircle color="success" />
                          ) : (
                            <ErrorIcon color="error" />
                          )}
                          <Box sx={{ flexGrow: 1 }}>
                            <Typography
                              variant="subtitle2"
                              sx={{ fontWeight: 600 }}
                            >
                              Test Data Item {result.test_data_index + 1}
                            </Typography>
                            {result.total_execution_time && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                Execution Time:{" "}
                                {result.total_execution_time.toFixed(2)} ms
                              </Typography>
                            )}
                          </Box>
                          <Chip
                            label={result.overall_passed ? "Passed" : "Failed"}
                            size="small"
                            color={result.overall_passed ? "success" : "error"}
                          />
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box
                          sx={{
                            display: "flex",
                            flexDirection: "column",
                            gap: 2,
                          }}
                        >
                          {result.results.map((scriptResult, sIndex) => (
                            <Card key={sIndex} variant="outlined">
                              <Box sx={{ p: 2 }}>
                                <Box
                                  sx={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: 1,
                                    mb: 1,
                                  }}
                                >
                                  {scriptResult.passed ? (
                                    <CheckCircle
                                      color="success"
                                      fontSize="small"
                                    />
                                  ) : (
                                    <ErrorIcon color="error" fontSize="small" />
                                  )}
                                  <Typography
                                    variant="subtitle2"
                                    sx={{ fontWeight: 600 }}
                                  >
                                    {scriptResult.script_type}
                                  </Typography>
                                  <Chip
                                    label={
                                      scriptResult.passed ? "Passed" : "Failed"
                                    }
                                    size="small"
                                    color={
                                      scriptResult.passed ? "success" : "error"
                                    }
                                  />
                                </Box>
                                {scriptResult.error_message && (
                                  <Alert severity="error" sx={{ mt: 1 }}>
                                    {scriptResult.error_message}
                                  </Alert>
                                )}
                                {scriptResult.script_output && (
                                  <Box sx={{ mt: 1 }}>
                                    <Typography
                                      variant="caption"
                                      color="text.secondary"
                                    >
                                      Script Output:
                                    </Typography>
                                    <CodeViewer
                                      code={scriptResult.script_output}
                                      language="text"
                                    />
                                  </Box>
                                )}
                              </Box>
                            </Card>
                          ))}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        </TabPanel>

        {/* Request-Response Verification Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Verify request-response pairs against validation scripts. Provide
              pairs in a structured format.
            </Typography>

            <EndpointAutocomplete
              value={selectedEndpointName}
              onChange={(value) => {
                const endpointName = Array.isArray(value)
                  ? value[0] || ""
                  : value;
                setSelectedEndpointName(endpointName);
                setSelectedEndpoint({
                  method: "GET",
                  path: "/api/example",
                  baseUrl: "https://api.example.com",
                });
              }}
              label="Select Endpoint"
            />

            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Request-Response Pairs
              </Typography>
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={addRequestResponseItem}
              >
                Add Pair
              </Button>
            </Box>

            {requestResponseItems.map((item, index) => (
              <Card key={item.id} variant="outlined" sx={{ p: 2 }}>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 2,
                  }}
                >
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Request-Response Pair {index + 1}
                  </Typography>
                  <Box>
                    <IconButton
                      size="small"
                      onClick={() => removeRequestResponseItem(item.id)}
                      disabled={requestResponseItems.length === 1}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>

                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <FormControl fullWidth>
                      <InputLabel>Method</InputLabel>
                      <Select
                        value={item.method || ""}
                        onChange={(e) =>
                          updateRequestResponseItem(
                            item.id,
                            "method",
                            e.target.value
                          )
                        }
                      >
                        <MenuItem value="GET">GET</MenuItem>
                        <MenuItem value="POST">POST</MenuItem>
                        <MenuItem value="PUT">PUT</MenuItem>
                        <MenuItem value="PATCH">PATCH</MenuItem>
                        <MenuItem value="DELETE">DELETE</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, md: 9 }}>
                    <TextField
                      label="Path"
                      value={item.path || ""}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "path",
                          e.target.value
                        )
                      }
                      fullWidth
                      placeholder="/api/users"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Query Parameters (JSON)"
                      value={item.params}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "params",
                          e.target.value
                        )
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"page": 1, "limit": 10}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Headers (JSON)"
                      value={item.headers}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "headers",
                          e.target.value
                        )
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"Content-Type": "application/json"}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12 }}>
                    <TextField
                      label="Request Body (JSON)"
                      value={item.body}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "body",
                          e.target.value
                        )
                      }
                      multiline
                      rows={4}
                      fullWidth
                      placeholder='{"name": "John Doe", "email": "john@example.com"}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Expected Status Code"
                      type="number"
                      value={item.expectedStatus}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "expectedStatus",
                          Number(e.target.value)
                        )
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Timeout (seconds)"
                      type="number"
                      value={item.timeout}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "timeout",
                          Number(e.target.value)
                        )
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Response Headers (JSON)"
                      value={item.responseHeaders}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "responseHeaders",
                          e.target.value
                        )
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"Content-Type": "application/json"}'
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Response Body (JSON)"
                      value={item.responseBody}
                      onChange={(e) =>
                        updateRequestResponseItem(
                          item.id,
                          "responseBody",
                          e.target.value
                        )
                      }
                      multiline
                      rows={3}
                      fullWidth
                      placeholder='{"id": 1, "name": "John Doe"}'
                    />
                  </Grid>
                </Grid>
              </Card>
            ))}

            {requestResponseError && (
              <Alert severity="error">
                Failed to verify request-response pairs. Please check your input
                and try again.
              </Alert>
            )}

            {isVerifyingRequestResponse && (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Verifying request-response pairs...
                </Typography>
                <LinearProgress />
              </Box>
            )}

            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleVerifyRequestResponse}
              disabled={!selectedEndpointName || isVerifyingRequestResponse}
              size="large"
            >
              {isVerifyingRequestResponse
                ? "Verifying..."
                : "Verify Request-Response"}
            </Button>

            {/* Request-Response Results */}
            {requestResponseResult && (
              <Box>
                <Divider sx={{ my: 3 }} />
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Verification Results
                </Typography>

                <Alert
                  severity={
                    requestResponseResult.overall_passed ? "success" : "error"
                  }
                  icon={
                    requestResponseResult.overall_passed ? (
                      <CheckCircle />
                    ) : (
                      <ErrorIcon />
                    )
                  }
                  sx={{ mb: 2 }}
                >
                  {requestResponseResult.overall_passed
                    ? `All ${requestResponseResult.total_pairs} request-response pairs passed verification`
                    : `Some request-response pairs failed verification`}
                </Alert>

                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {requestResponseResult.verification_results.map(
                    (result, index) => (
                      <Accordion
                        key={index}
                        expanded={
                          expandedRequestResponseResult === `pair-${index}`
                        }
                        onChange={handleRequestResponseAccordionChange(
                          `pair-${index}`
                        )}
                      >
                        <AccordionSummary expandIcon={<ExpandMore />}>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 2,
                              flexGrow: 1,
                            }}
                          >
                            {result.overall_passed ? (
                              <CheckCircle color="success" />
                            ) : (
                              <ErrorIcon color="error" />
                            )}
                            <Box sx={{ flexGrow: 1 }}>
                              <Typography
                                variant="subtitle2"
                                sx={{ fontWeight: 600 }}
                              >
                                Request-Response Pair {result.pair_index + 1}
                              </Typography>
                              {result.total_execution_time && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  Execution Time:{" "}
                                  {result.total_execution_time.toFixed(2)} ms
                                </Typography>
                              )}
                            </Box>
                            <Chip
                              label={
                                result.overall_passed ? "Passed" : "Failed"
                              }
                              size="small"
                              color={
                                result.overall_passed ? "success" : "error"
                              }
                            />
                          </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Box
                            sx={{
                              display: "flex",
                              flexDirection: "column",
                              gap: 2,
                            }}
                          >
                            {result.results.map((scriptResult, sIndex) => (
                              <Card key={sIndex} variant="outlined">
                                <Box sx={{ p: 2 }}>
                                  <Box
                                    sx={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 1,
                                      mb: 1,
                                    }}
                                  >
                                    {scriptResult.passed ? (
                                      <CheckCircle
                                        color="success"
                                        fontSize="small"
                                      />
                                    ) : (
                                      <ErrorIcon
                                        color="error"
                                        fontSize="small"
                                      />
                                    )}
                                    <Typography
                                      variant="subtitle2"
                                      sx={{ fontWeight: 600 }}
                                    >
                                      {scriptResult.script_type}
                                    </Typography>
                                    <Chip
                                      label={
                                        scriptResult.passed
                                          ? "Passed"
                                          : "Failed"
                                      }
                                      size="small"
                                      color={
                                        scriptResult.passed
                                          ? "success"
                                          : "error"
                                      }
                                    />
                                  </Box>
                                  {scriptResult.error_message && (
                                    <Alert severity="error" sx={{ mt: 1 }}>
                                      {scriptResult.error_message}
                                    </Alert>
                                  )}
                                  {scriptResult.script_output && (
                                    <Box sx={{ mt: 1 }}>
                                      <Typography
                                        variant="caption"
                                        color="text.secondary"
                                      >
                                        Script Output:
                                      </Typography>
                                      <CodeViewer
                                        code={scriptResult.script_output}
                                        language="text"
                                      />
                                    </Box>
                                  )}
                                </Box>
                              </Card>
                            ))}
                          </Box>
                        </AccordionDetails>
                      </Accordion>
                    )
                  )}
                </Box>
              </Box>
            )}
          </Box>
        </TabPanel>
      </Card>
    </Box>
  );
};

export default VerificationPage;
