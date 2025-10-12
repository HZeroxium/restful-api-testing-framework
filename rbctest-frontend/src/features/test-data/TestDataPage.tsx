import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Chip,
  Switch,
  FormControlLabel,
  Grid,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TablePagination,
} from "@mui/material";
import {
  Search,
  DataObject,
  FilterList,
  Add,
  ExpandMore,
} from "@mui/icons-material";
import {
  useGetEndpointsQuery,
  useGenerateTestDataMutation,
  useGetAllTestDataQuery,
} from "@/services/api";
import { CodeViewer } from "@/components/common/CodeViewer";
import EndpointAutocomplete from "@/components/common/EndpointAutocomplete";
import { usePagination } from "@/hooks/usePagination";

const TestDataPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const endpointNameFromQuery = searchParams.get("endpoint") || "";

  const {
    page,
    pageSize,
    offset,
    limit,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  } = usePagination({ defaultPageSize: 20 });
  const [searchTerm, setSearchTerm] = useState("");
  const [validityFilter, setValidityFilter] = useState<string>("all");
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [expandedTestData, setExpandedTestData] = useState<string | null>(null);

  const [selectedEndpointName, setSelectedEndpointName] = useState(
    endpointNameFromQuery
  );
  const [testDataCount, setTestDataCount] = useState(5);
  const [includeInvalid, setIncludeInvalid] = useState(true);
  const [overrideExisting, setOverrideExisting] = useState(false);

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination();
  }, [searchTerm, validityFilter, resetPagination]);

  const { data: endpointsData } = useGetEndpointsQuery({
    limit: 100,
    offset: 0,
  });
  const [
    generateTestData,
    { isLoading: isGenerating, error: generateError, data: generatedData },
  ] = useGenerateTestDataMutation();

  // Fetch all test data from backend
  const {
    data: allTestDataData,
    isLoading: isLoadingTestData,
    error: testDataError,
    refetch: refetchTestData,
  } = useGetAllTestDataQuery({ limit, offset });

  const endpoints = endpointsData?.endpoints || [];

  // Combine backend test data with generated data
  const testDataItems = [
    ...(allTestDataData?.test_data_items || []),
    ...(generatedData?.test_data_items || []),
  ];

  // Check if client-side filtering is active
  const hasActiveFilters = searchTerm !== "" || validityFilter !== "all";

  // Filter test data (only when filters are active)
  const filteredTestData = hasActiveFilters
    ? testDataItems.filter((item) => {
        const matchesSearch =
          searchTerm === "" ||
          item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.description.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesValidity =
          validityFilter === "all" ||
          (validityFilter === "valid" && item.is_valid) ||
          (validityFilter === "invalid" && !item.is_valid);

        return matchesSearch && matchesValidity;
      })
    : testDataItems;

  const handleGenerateTestData = async () => {
    if (!selectedEndpointName) return;

    try {
      await generateTestData({
        endpointName: selectedEndpointName,
        body: {
          count: testDataCount,
          include_invalid_data: includeInvalid,
          override_existing: overrideExisting,
        },
      }).unwrap();
      setGenerateDialogOpen(false);
    } catch (err) {
      console.error("Failed to generate test data:", err);
    }
  };

  const handleAccordionChange =
    (testDataId: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedTestData(isExpanded ? testDataId : null);
    };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 1,
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              component="h1"
              sx={{ fontWeight: 600, mb: 1 }}
            >
              Test Data
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generate and manage test data for your endpoints
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setGenerateDialogOpen(true)}
          >
            Generate Test Data
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              gap: 2,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <TextField
              placeholder="Search test data..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              size="small"
              sx={{ flexGrow: 1, minWidth: 200 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search />
                  </InputAdornment>
                ),
              }}
            />

            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Validity</InputLabel>
              <Select
                value={validityFilter}
                label="Validity"
                onChange={(e) => setValidityFilter(e.target.value)}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="valid">Valid Only</MenuItem>
                <MenuItem value="invalid">Invalid Only</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterList fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {filteredTestData.length} of {testDataItems.length} items
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Test Data Table or Empty State */}
      <Card>
        <CardContent>
          {isLoadingTestData ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="text.secondary">
                Loading test data...
              </Typography>
            </Box>
          ) : testDataError ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="error" gutterBottom>
                Error loading test data
              </Typography>
              <Button variant="outlined" onClick={() => refetchTestData()}>
                Retry
              </Button>
            </Box>
          ) : testDataItems.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <DataObject
                sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
              />
              <Typography variant="h6" gutterBottom>
                No test data available
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Generate test data for your endpoints to get started
              </Typography>
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setGenerateDialogOpen(true)}
              >
                Generate Test Data
              </Button>
            </Box>
          ) : filteredTestData.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="text.secondary">
                No test data matches your filters
              </Typography>
            </Box>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {filteredTestData.map((testData) => (
                <Accordion
                  key={testData.id}
                  expanded={expandedTestData === testData.id}
                  onChange={handleAccordionChange(testData.id)}
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
                      <DataObject color="primary" />
                      <Box sx={{ flexGrow: 1 }}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                            mb: 0.5,
                          }}
                        >
                          <Typography
                            variant="subtitle1"
                            sx={{ fontWeight: 600 }}
                          >
                            Test Data #{testData.id.slice(0, 8)}...
                          </Typography>
                          <Chip
                            label={testData.is_valid ? "Valid" : "Invalid"}
                            size="small"
                            color={testData.is_valid ? "success" : "error"}
                            variant="outlined"
                          />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Endpoint:{" "}
                          {endpoints.find((e) => e.id === testData.endpoint_id)
                            ?.name || testData.endpoint_id}
                        </Typography>
                      </Box>
                      <Chip
                        label={`${
                          testData.request_params
                            ? Object.keys(testData.request_params).length
                            : 0
                        } params`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box
                      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
                    >
                      <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Endpoint
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {endpoints.find(
                              (e) => e.id === testData.endpoint_id
                            )?.name || testData.endpoint_id}
                          </Typography>
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Validity Status
                          </Typography>
                          <Chip
                            label={testData.is_valid ? "Valid" : "Invalid"}
                            color={testData.is_valid ? "success" : "error"}
                            variant="outlined"
                          />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Expected Status Code
                          </Typography>
                          <Chip
                            label={testData.expected_status_code || "N/A"}
                            color="primary"
                            variant="outlined"
                          />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Name
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {testData.name}
                          </Typography>
                        </Grid>
                      </Grid>

                      <Divider />

                      <Box>
                        <Typography variant="subtitle2" gutterBottom>
                          Description
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {testData.description}
                        </Typography>
                      </Box>

                      {testData.request_params &&
                        Object.keys(testData.request_params).length > 0 && (
                          <>
                            <Divider />
                            <Box>
                              <Typography variant="subtitle2" gutterBottom>
                                Request Parameters
                              </Typography>
                              <CodeViewer
                                code={JSON.stringify(
                                  testData.request_params,
                                  null,
                                  2
                                )}
                                language="json"
                              />
                            </Box>
                          </>
                        )}

                      {testData.request_body && (
                        <>
                          <Divider />
                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              Request Body
                            </Typography>
                            <CodeViewer
                              code={JSON.stringify(
                                testData.request_body,
                                null,
                                2
                              )}
                              language="json"
                            />
                          </Box>
                        </>
                      )}

                      {testData.expected_response_schema && (
                        <>
                          <Divider />
                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              Expected Response Schema
                            </Typography>
                            <CodeViewer
                              code={JSON.stringify(
                                testData.expected_response_schema,
                                null,
                                2
                              )}
                              language="json"
                            />
                          </Box>
                        </>
                      )}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}

          {/* Pagination */}
          {!hasActiveFilters && (
            <TablePagination
              component="div"
              count={allTestDataData?.pagination.total_items || 0}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={pageSize}
              onRowsPerPageChange={handlePageSizeChange}
              rowsPerPageOptions={[10, 20, 50, 100]}
              labelRowsPerPage="Rows per page:"
              labelDisplayedRows={({ from, to, count }) =>
                `${from}–${to} of ${count !== -1 ? count : `more than ${to}`}`
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Generate Test Data Dialog */}
      <Dialog
        open={generateDialogOpen}
        onClose={() => setGenerateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Generate Test Data</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Generate test data for an endpoint based on its schema and
              constraints.
            </Typography>

            {generateError && (
              <Alert severity="error">
                Failed to generate test data. Please try again.
              </Alert>
            )}

            <EndpointAutocomplete
              value={selectedEndpointName}
              onChange={(value) =>
                setSelectedEndpointName(
                  Array.isArray(value) ? value[0] || "" : value
                )
              }
              label="Select Endpoint"
            />

            <TextField
              label="Number of Test Cases"
              type="number"
              value={testDataCount}
              onChange={(e) =>
                setTestDataCount(Math.max(1, parseInt(e.target.value) || 1))
              }
              fullWidth
              InputProps={{ inputProps: { min: 1, max: 50 } }}
            />

            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={includeInvalid}
                    onChange={(e) => setIncludeInvalid(e.target.checked)}
                  />
                }
                label="Include Invalid Test Data"
              />
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Generate both valid and invalid test cases to test error
                handling
              </Typography>
            </Box>

            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={overrideExisting}
                    onChange={(e) => setOverrideExisting(e.target.checked)}
                    color="warning"
                  />
                }
                label="Override Existing Test Data"
              />
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Delete existing test data before generating new data
              </Typography>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGenerateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleGenerateTestData}
            variant="contained"
            disabled={!selectedEndpointName || isGenerating}
          >
            {isGenerating ? "Generating..." : "Generate"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TestDataPage;
