import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Chip,
  LinearProgress,
} from "@mui/material";
import { Search, PlayArrow, FilterList, Refresh } from "@mui/icons-material";
import { format } from "date-fns";
import {
  useGetEndpointsQuery,
  useExecuteTestsByEndpointNameMutation,
  useGetTestDataByEndpointNameQuery,
  useGetExecutionHistoryByEndpointNameQuery,
  useGetAllExecutionsQuery,
} from "@/services/api";
import { DataTable } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { ExecutionHistoryResponse, TableColumn } from "@/types";

const ExecutionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const endpointNameFromQuery = searchParams.get("endpoint") || "";

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);

  const [selectedEndpointName, setSelectedEndpointName] = useState(
    endpointNameFromQuery
  );
  const [baseUrl, setBaseUrl] = useState("");
  const [timeout, setTimeout] = useState(30);

  const { data: endpointsData } = useGetEndpointsQuery({ page: 1, size: 100 });
  const { data: testDataData } = useGetTestDataByEndpointNameQuery(
    selectedEndpointName,
    {
      skip: !selectedEndpointName,
    }
  );

  const [
    executeTests,
    { isLoading: isExecuting, error: executeError, data: executionResult },
  ] = useExecuteTestsByEndpointNameMutation();

  const [executions, setExecutions] = useState<ExecutionHistoryResponse[]>([]);
  const [pollingEnabled, setPollingEnabled] = useState(false);

  const endpoints = endpointsData?.endpoints || [];
  const testDataItems = testDataData?.test_data_items || [];

  // Fetch all executions from backend
  const {
    data: allExecutionsData,
    isLoading: isLoadingExecutions,
    error: executionsError,
    refetch: refetchExecutions,
  } = useGetAllExecutionsQuery({ limit: 1000, offset: 0 });

  const allExecutions = allExecutionsData?.executions || [];

  // Simulate polling for executions (in real app, would use RTK Query polling or WebSocket)
  useEffect(() => {
    if (executionResult) {
      const newExecution: ExecutionHistoryResponse = {
        id: executionResult.execution_id,
        endpoint_id: executionResult.endpoint_id,
        endpoint_name: executionResult.endpoint_name,
        base_url: executionResult.base_url,
        overall_status: executionResult.overall_status,
        total_tests: executionResult.total_tests,
        passed_tests: executionResult.passed_tests,
        failed_tests: executionResult.failed_tests,
        success_rate: executionResult.success_rate,
        total_execution_time_ms: executionResult.total_execution_time_ms,
        started_at: executionResult.started_at,
        completed_at:
          executionResult.completed_at || executionResult.started_at,
        error_message: executionResult.error_message || "",
        test_data_used: [],
      };

      setExecutions((prev) => [newExecution, ...prev]);
    }
  }, [executionResult]);

  // Combine local executions with API executions
  const combinedExecutions = [...executions, ...allExecutions];

  // Filter executions
  const filteredExecutions = combinedExecutions.filter((execution) => {
    const matchesSearch =
      searchTerm === "" ||
      execution.endpoint_name.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" || execution.overall_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleExecuteTests = async () => {
    if (!selectedEndpointName || !baseUrl) return;

    try {
      await executeTests({
        endpointName: selectedEndpointName,
        body: {
          base_url: baseUrl,
          timeout,
        },
      }).unwrap();

      setExecuteDialogOpen(false);
      setSelectedEndpointName("");
      setBaseUrl("");
    } catch (err) {
      console.error("Failed to execute tests:", err);
    }
  };

  const columns: TableColumn<ExecutionHistoryResponse>[] = [
    {
      key: "overall_status",
      label: "Status",
      sortable: true,
      render: (value: string) => <StatusBadge status={value} />,
    },
    {
      key: "endpoint_name",
      label: "Endpoint",
      sortable: true,
      render: (value: string) => (
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {value}
        </Typography>
      ),
    },
    {
      key: "base_url",
      label: "Base URL",
      render: (value: string) => (
        <Typography
          variant="body2"
          sx={{ fontFamily: "monospace", fontSize: "0.875rem" }}
        >
          {value}
        </Typography>
      ),
    },
    {
      key: "total_tests",
      label: "Total Tests",
      sortable: true,
    },
    {
      key: "passed_tests",
      label: "Passed",
      sortable: true,
      render: (value: number) => (
        <Chip label={value} size="small" color="success" />
      ),
    },
    {
      key: "failed_tests",
      label: "Failed",
      sortable: true,
      render: (value: number) => (
        <Chip label={value} size="small" color="error" />
      ),
    },
    {
      key: "success_rate",
      label: "Success Rate",
      sortable: true,
      render: (value: number) => `${(value * 100).toFixed(1)}%`,
    },
    {
      key: "started_at",
      label: "Started At",
      sortable: true,
      render: (value: string) =>
        format(new Date(value), "MMM dd, yyyy HH:mm:ss"),
    },
  ];

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
              Test Executions
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Execute and monitor test runs for your endpoints
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => setPollingEnabled(!pollingEnabled)}
            >
              {pollingEnabled ? "Stop Polling" : "Start Polling"}
            </Button>
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={() => setExecuteDialogOpen(true)}
            >
              Execute Tests
            </Button>
          </Box>
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
              placeholder="Search executions..."
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
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All Statuses</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="running">Running</MenuItem>
                <MenuItem value="failed">Failed</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterList fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {filteredExecutions.length} of {combinedExecutions.length}{" "}
                executions
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Executions Table */}
      <Card>
        <CardContent>
          {isLoadingExecutions ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="text.secondary">
                Loading executions...
              </Typography>
            </Box>
          ) : executionsError ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="error" gutterBottom>
                Error loading executions
              </Typography>
              <Button variant="outlined" onClick={() => refetchExecutions()}>
                Retry
              </Button>
            </Box>
          ) : combinedExecutions.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <PlayArrow
                sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
              />
              <Typography variant="h6" gutterBottom>
                No test executions yet
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Execute tests for your endpoints to see results here
              </Typography>
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                onClick={() => setExecuteDialogOpen(true)}
              >
                Execute Tests
              </Button>
            </Box>
          ) : filteredExecutions.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Typography variant="body1" color="text.secondary">
                No executions match your filters
              </Typography>
            </Box>
          ) : (
            <DataTable
              columns={columns}
              data={filteredExecutions}
              onRowClick={(execution: any) =>
                navigate(`/executions/${execution.id}`)
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Execute Tests Dialog */}
      <Dialog
        open={executeDialogOpen}
        onClose={() => !isExecuting && setExecuteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Execute Tests</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Execute test cases for an endpoint against a live API.
            </Typography>

            {executeError && (
              <Alert severity="error">
                Failed to execute tests. Please try again.
              </Alert>
            )}

            {isExecuting && (
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Executing tests...
                </Typography>
                <LinearProgress />
              </Box>
            )}

            <FormControl fullWidth>
              <InputLabel>Select Endpoint</InputLabel>
              <Select
                value={selectedEndpointName}
                label="Select Endpoint"
                onChange={(e) => setSelectedEndpointName(e.target.value)}
                disabled={isExecuting}
              >
                {endpoints.map((endpoint) => (
                  <MenuItem key={endpoint.id} value={endpoint.name}>
                    {endpoint.method} {endpoint.path} - {endpoint.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {selectedEndpointName && (
              <Alert severity="info">
                {testDataItems.length} test case
                {testDataItems.length !== 1 ? "s" : ""} available for this
                endpoint
              </Alert>
            )}

            <TextField
              label="Base URL"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              fullWidth
              disabled={isExecuting}
              placeholder="https://api.example.com"
              helperText="The base URL of the API to test against"
            />

            <TextField
              label="Timeout (seconds)"
              type="number"
              value={timeout}
              onChange={(e) =>
                setTimeout(Math.max(1, parseInt(e.target.value) || 30))
              }
              fullWidth
              disabled={isExecuting}
              InputProps={{ inputProps: { min: 1, max: 300 } }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setExecuteDialogOpen(false)}
            disabled={isExecuting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleExecuteTests}
            variant="contained"
            disabled={!selectedEndpointName || !baseUrl || isExecuting}
          >
            {isExecuting ? "Executing..." : "Execute"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExecutionsPage;
