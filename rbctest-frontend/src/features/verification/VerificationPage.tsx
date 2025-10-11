import React, { useState } from "react";
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  LinearProgress,
} from "@mui/material";
import {
  ExpandMore,
  CheckCircle,
  Error as ErrorIcon,
  PlayArrow,
} from "@mui/icons-material";
import {
  useGetEndpointsQuery,
  useVerifyTestDataMutation,
  useVerifyRequestResponseMutation,
} from "@/services/api";
import { CodeViewer } from "@/components/common/CodeViewer";
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

const VerificationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedEndpointName, setSelectedEndpointName] = useState("");

  // Test Data Verification
  const [testDataJson, setTestDataJson] = useState(
    '[\n  {\n    "request_body": {},\n    "expected_status_code": 200\n  }\n]'
  );
  const [
    verifyTestData,
    {
      isLoading: isVerifyingTestData,
      data: testDataResult,
      error: testDataError,
    },
  ] = useVerifyTestDataMutation();

  // Request-Response Verification
  const [requestResponseJson, setRequestResponseJson] = useState(
    '[\n  {\n    "request": {},\n    "response": {}\n  }\n]'
  );
  const [
    verifyRequestResponse,
    {
      isLoading: isVerifyingRequestResponse,
      data: requestResponseResult,
      error: requestResponseError,
    },
  ] = useVerifyRequestResponseMutation();

  const { data: endpointsData } = useGetEndpointsQuery({ page: 1, size: 100 });
  const endpoints = endpointsData?.endpoints || [];

  const [expandedTestDataResult, setExpandedTestDataResult] = useState<
    string | false
  >(false);
  const [expandedRequestResponseResult, setExpandedRequestResponseResult] =
    useState<string | false>(false);

  const handleVerifyTestData = async () => {
    if (!selectedEndpointName) return;

    try {
      const testDataItems: TestDataItem[] = JSON.parse(testDataJson);
      await verifyTestData({
        endpointName: selectedEndpointName,
        body: {
          test_data_items: testDataItems,
        },
      }).unwrap();
    } catch (err) {
      console.error("Failed to verify test data:", err);
    }
  };

  const handleVerifyRequestResponse = async () => {
    if (!selectedEndpointName) return;

    try {
      const pairs: RequestResponsePair[] = JSON.parse(requestResponseJson);
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
              Provide test data in JSON format.
            </Typography>

            <FormControl fullWidth>
              <InputLabel>Select Endpoint</InputLabel>
              <Select
                value={selectedEndpointName}
                label="Select Endpoint"
                onChange={(e) => setSelectedEndpointName(e.target.value)}
              >
                {endpoints.map((endpoint) => (
                  <MenuItem key={endpoint.id} value={endpoint.name}>
                    {endpoint.method} {endpoint.path} - {endpoint.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: 600 }}
              >
                Test Data (JSON Array)
              </Typography>
              <TextField
                value={testDataJson}
                onChange={(e) => setTestDataJson(e.target.value)}
                multiline
                rows={10}
                fullWidth
                placeholder='[{"request_body": {}, "expected_status_code": 200}]'
                sx={{ fontFamily: "monospace" }}
              />
            </Box>

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
              pairs in JSON format.
            </Typography>

            <FormControl fullWidth>
              <InputLabel>Select Endpoint</InputLabel>
              <Select
                value={selectedEndpointName}
                label="Select Endpoint"
                onChange={(e) => setSelectedEndpointName(e.target.value)}
              >
                {endpoints.map((endpoint) => (
                  <MenuItem key={endpoint.id} value={endpoint.name}>
                    {endpoint.method} {endpoint.path} - {endpoint.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: 600 }}
              >
                Request-Response Pairs (JSON Array)
              </Typography>
              <TextField
                value={requestResponseJson}
                onChange={(e) => setRequestResponseJson(e.target.value)}
                multiline
                rows={10}
                fullWidth
                placeholder='[{"request": {}, "response": {}}]'
                sx={{ fontFamily: "monospace" }}
              />
            </Box>

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
