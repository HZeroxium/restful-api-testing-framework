import React, { useState } from "react";
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  TextField,
  Chip,
  // Alert,
  Card,
  CardContent,
  FormControlLabel,
  Switch,
} from "@mui/material";
import { PlayArrow, Search, SelectAll, Clear } from "@mui/icons-material";
import Grid from "@mui/material/Grid";
import { useGetAvailableEndpointsForBatchQuery } from "@/services/api";
import BatchProgressDialog from "@/components/common/BatchProgressDialog";
import type { BatchResult } from "@/types";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`batch-tabpanel-${index}`}
      aria-labelledby={`batch-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function BatchOperationsPage() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedEndpoints, setSelectedEndpoints] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [useMockApi, setUseMockApi] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [showResults, setShowResults] = useState(false);

  const { data: endpointsData, isLoading: isLoadingEndpoints } =
    useGetAvailableEndpointsForBatchQuery();

  const endpoints = endpointsData?.endpoints || [];
  const filteredEndpoints = endpoints.filter((endpoint) =>
    endpoint.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSelectAll = () => {
    if (selectedEndpoints.length === filteredEndpoints.length) {
      setSelectedEndpoints([]);
    } else {
      setSelectedEndpoints(filteredEndpoints.map((ep) => ep.name));
    }
  };

  const handleSelectEndpoint = (endpointName: string) => {
    setSelectedEndpoints((prev) =>
      prev.includes(endpointName)
        ? prev.filter((name) => name !== endpointName)
        : [...prev, endpointName]
    );
  };

  const handleExecute = async () => {
    if (selectedEndpoints.length === 0) {
      alert("Please select at least one endpoint");
      return;
    }

    if (!baseUrl.trim()) {
      alert("Please enter a base URL");
      return;
    }

    setIsLoading(true);
    setResults([]);
    setShowResults(true);

    // Simulate batch operation
    setTimeout(() => {
      const mockResults: BatchResult[] = selectedEndpoints.map(
        (endpointName) => ({
          endpoint_name: endpointName,
          success: Math.random() > 0.2, // 80% success rate
          execution_time_ms: Math.random() * 2000 + 500,
          details: {},
          error_message: Math.random() > 0.8 ? "Simulated error" : "",
        })
      );

      setResults(mockResults);
      setIsLoading(false);
    }, 3000);
  };

  const handleClearResults = () => {
    setResults([]);
    setShowResults(false);
  };

  const getOperationName = () => {
    switch (tabValue) {
      case 0:
        return "Batch Mine Constraints";
      case 1:
        return "Batch Generate Validation Scripts";
      case 2:
        return "Batch Full Pipeline";
      default:
        return "Batch Operation";
    }
  };

  const successCount = results.filter((r) => r.success).length;
  const totalTime = results.reduce((sum, r) => sum + r.execution_time_ms, 0);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Batch Operations
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Mine Constraints" />
          <Tab label="Generate Scripts" />
          <Tab label="Full Pipeline" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Typography variant="h6" gutterBottom>
            Batch Mine Constraints
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Mine constraints for multiple endpoints in parallel to analyze API
            specifications.
          </Typography>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Batch Generate Validation Scripts
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Generate validation scripts for multiple endpoints based on their
            constraints.
          </Typography>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Typography variant="h6" gutterBottom>
            Batch Full Pipeline
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Run the complete testing pipeline (mine → generate → test → execute)
            for multiple endpoints.
          </Typography>
        </TabPanel>
      </Paper>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <TextField
                label="Search endpoints"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <Search sx={{ mr: 1, color: "text.secondary" }} />
                  ),
                }}
                sx={{ flexGrow: 1 }}
              />
              <Button
                startIcon={<SelectAll />}
                onClick={handleSelectAll}
                variant="outlined"
              >
                {selectedEndpoints.length === filteredEndpoints.length
                  ? "Clear All"
                  : "Select All"}
              </Button>
            </Box>

            <TableContainer sx={{ maxHeight: 400 }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={
                          selectedEndpoints.length > 0 &&
                          selectedEndpoints.length < filteredEndpoints.length
                        }
                        checked={
                          selectedEndpoints.length ===
                            filteredEndpoints.length &&
                          filteredEndpoints.length > 0
                        }
                        onChange={handleSelectAll}
                      />
                    </TableCell>
                    <TableCell>Endpoint</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Path</TableCell>
                    <TableCell>Dataset</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {isLoadingEndpoints ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        Loading endpoints...
                      </TableCell>
                    </TableRow>
                  ) : filteredEndpoints.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No endpoints found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredEndpoints.map((endpoint) => (
                      <TableRow key={endpoint.id} hover>
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedEndpoints.includes(endpoint.name)}
                            onChange={() => handleSelectEndpoint(endpoint.name)}
                          />
                        </TableCell>
                        <TableCell>{endpoint.name}</TableCell>
                        <TableCell>
                          <Chip
                            label={endpoint.method}
                            size="small"
                            color="primary"
                          />
                        </TableCell>
                        <TableCell>{endpoint.path}</TableCell>
                        <TableCell>{endpoint.dataset_id || "N/A"}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Configuration
            </Typography>

            <TextField
              label="Base URL"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              fullWidth
              margin="normal"
              placeholder="https://api.example.com"
              helperText="Base URL for API calls"
            />

            <FormControlLabel
              control={
                <Switch
                  checked={useMockApi}
                  onChange={(e) => setUseMockApi(e.target.checked)}
                />
              }
              label="Use Mock API"
              sx={{ mt: 2 }}
            />

            <Box sx={{ mt: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Selected Endpoints: {selectedEndpoints.length}
              </Typography>
              {selectedEndpoints.length > 0 && (
                <Box sx={{ maxHeight: 150, overflow: "auto" }}>
                  {selectedEndpoints.map((name) => (
                    <Chip
                      key={name}
                      label={name}
                      size="small"
                      onDelete={() => handleSelectEndpoint(name)}
                      sx={{ m: 0.5 }}
                    />
                  ))}
                </Box>
              )}
            </Box>

            <Box sx={{ mt: 3, display: "flex", gap: 1 }}>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleExecute}
                disabled={
                  selectedEndpoints.length === 0 || !baseUrl.trim() || isLoading
                }
                fullWidth
              >
                Execute {getOperationName()}
              </Button>
            </Box>

            {showResults && (
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<Clear />}
                  onClick={handleClearResults}
                  size="small"
                >
                  Clear Results
                </Button>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {showResults && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Execution Results
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Total Endpoints
                </Typography>
                <Typography variant="h6">{results.length}</Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Successful
                </Typography>
                <Typography variant="h6" color="success.main">
                  {successCount}
                </Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Failed
                </Typography>
                <Typography variant="h6" color="error.main">
                  {results.length - successCount}
                </Typography>
              </Grid>
              <Grid size={{ xs: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Total Time
                </Typography>
                <Typography variant="h6">{totalTime.toFixed(0)}ms</Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      <BatchProgressDialog
        open={showResults}
        onClose={() => setShowResults(false)}
        title={getOperationName()}
        results={results}
        isLoading={isLoading}
      />
    </Box>
  );
}
