import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Grid,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
} from "@mui/material";
import {
  ArrowBack,
  Delete,
  BugReport,
  Code,
  DataObject,
  PlayArrow,
  ExpandMore,
  CheckCircle,
  Error,
  Warning,
  Info,
} from "@mui/icons-material";
import {
  useGetEndpointQuery,
  useDeleteEndpointMutation,
  useGetConstraintsByEndpointIdQuery,
  useGetScriptsByEndpointIdQuery,
  useGetTestDataByEndpointIdQuery,
  useGetExecutionHistoryByEndpointIdQuery,
  useMineConstraintsByEndpointNameMutation,
  useGenerateScriptsByEndpointNameMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { CodeViewer } from "@/components/common/CodeViewer";
import { DataTable } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
  </div>
);

const EndpointDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(0);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const {
    data: endpoint,
    isLoading: isLoadingEndpoint,
    error: endpointError,
    refetch: refetchEndpoint,
  } = useGetEndpointQuery(id!);

  const {
    data: constraintsData,
    isLoading: isLoadingConstraints,
    refetch: refetchConstraints,
  } = useGetConstraintsByEndpointIdQuery(id!);

  const {
    data: scriptsData,
    isLoading: isLoadingScripts,
    refetch: refetchScripts,
  } = useGetScriptsByEndpointIdQuery(id!);

  const { data: testDataData, isLoading: isLoadingTestData } =
    useGetTestDataByEndpointIdQuery(id!);

  const { data: executionsData, isLoading: isLoadingExecutions } =
    useGetExecutionHistoryByEndpointIdQuery({ endpointId: id!, limit: 10 });

  const [deleteEndpoint] = useDeleteEndpointMutation();
  const [mineConstraints, { isLoading: isMiningConstraints }] =
    useMineConstraintsByEndpointNameMutation();
  const [generateScripts, { isLoading: isGeneratingScripts }] =
    useGenerateScriptsByEndpointNameMutation();

  const handleDelete = async () => {
    try {
      await deleteEndpoint(id!).unwrap();
      navigate("/endpoints");
    } catch (err) {
      console.error("Failed to delete endpoint:", err);
    }
  };

  const handleMineConstraints = async () => {
    if (!endpoint) return;
    try {
      await mineConstraints(endpoint.name).unwrap();
      refetchConstraints();
    } catch (err) {
      console.error("Failed to mine constraints:", err);
    }
  };

  const handleGenerateScripts = async () => {
    if (!endpoint) return;
    try {
      await generateScripts(endpoint.name).unwrap();
      refetchScripts();
    } catch (err) {
      console.error("Failed to generate scripts:", err);
    }
  };

  const isLoading = isLoadingEndpoint;
  const error = endpointError;

  if (isLoading) {
    return <LoadingOverlay open={true} />;
  }

  if (error || !endpoint) {
    return (
      <ErrorAlert
        error={
          error
            ? typeof error === "object" && "message" in error
              ? error.message
              : "An error occurred"
            : "Endpoint not found"
        }
        onRetry={refetchEndpoint}
      />
    );
  }

  const constraints = constraintsData?.constraints || [];
  const scripts = scriptsData?.scripts || [];
  const testDataItems = testDataData?.test_data_items || [];
  const executions = executionsData?.executions || [];

  const methodColors: Record<
    string,
    "success" | "primary" | "warning" | "error" | "default"
  > = {
    GET: "success",
    POST: "primary",
    PUT: "warning",
    DELETE: "error",
    PATCH: "warning",
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate("/endpoints")}
          sx={{ mb: 2 }}
        >
          Back to Endpoints
        </Button>

        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 2,
          }}
        >
          <Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 1 }}>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
                {endpoint.name}
              </Typography>
              <Chip
                label={endpoint.method}
                color={methodColors[endpoint.method] || "default"}
                sx={{ fontWeight: 600 }}
              />
            </Box>
            <Typography
              variant="body1"
              sx={{ fontFamily: "monospace", color: "text.secondary", mb: 1 }}
            >
              {endpoint.path}
            </Typography>
            {endpoint.description && (
              <Typography variant="body2" color="text.secondary">
                {endpoint.description}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Tooltip title="Delete Endpoint">
              <IconButton
                color="error"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Delete />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Box>

      {/* Metadata */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Authentication
              </Typography>
              <Chip
                label={
                  endpoint.auth_required
                    ? endpoint.auth_type || "Required"
                    : "None"
                }
                size="small"
                color={endpoint.auth_required ? "warning" : "default"}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Constraints
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {constraints.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Validation Scripts
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {scripts.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Test Data
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {testDataItems.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tags */}
      {endpoint.tags.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Tags
          </Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
            {endpoint.tags.map((tag) => (
              <Chip key={tag} label={tag} size="small" variant="outlined" />
            ))}
          </Box>
        </Box>
      )}

      {/* Tabs */}
      <Card>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="Schemas" />
          <Tab label={`Constraints (${constraints.length})`} />
          <Tab label={`Validation Scripts (${scripts.length})`} />
          <Tab label={`Test Data (${testDataItems.length})`} />
          <Tab label={`Executions (${executions.length})`} />
        </Tabs>

        <Divider />

        {/* Schema Tab */}
        <TabPanel value={activeTab} index={0}>
          <Box sx={{ px: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
              Request Schema
            </Typography>
            <CodeViewer
              code={JSON.stringify(endpoint.input_schema, null, 2)}
              language="json"
            />

            <Typography
              variant="h6"
              gutterBottom
              sx={{ fontWeight: 600, mt: 4 }}
            >
              Response Schema
            </Typography>
            <CodeViewer
              code={JSON.stringify(endpoint.output_schema, null, 2)}
              language="json"
            />
          </Box>
        </TabPanel>

        {/* Constraints Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ px: 3 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Constraints
              </Typography>
              <Button
                variant="contained"
                startIcon={<BugReport />}
                onClick={handleMineConstraints}
                disabled={isMiningConstraints}
              >
                {isMiningConstraints ? "Mining..." : "Mine Constraints"}
              </Button>
            </Box>

            {isLoadingConstraints ? (
              <LoadingOverlay open={true} />
            ) : constraints.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <BugReport
                  sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
                />
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  No constraints found
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<BugReport />}
                  onClick={handleMineConstraints}
                  disabled={isMiningConstraints}
                >
                  Mine Constraints
                </Button>
              </Box>
            ) : (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {constraints.map((constraint, index) => (
                  <Accordion key={constraint.id} defaultExpanded={index === 0}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}>
                        <Avatar sx={{ bgcolor: constraint.severity === 'error' ? 'error.main' : constraint.severity === 'warning' ? 'warning.main' : 'info.main', width: 32, height: 32 }}>
                          {constraint.severity === 'error' ? <Error fontSize="small" /> : constraint.severity === 'warning' ? <Warning fontSize="small" /> : <Info fontSize="small" />}
                        </Avatar>
                        <Box sx={{ flexGrow: 1 }}>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {constraint.description}
                            </Typography>
                            <StatusBadge status={constraint.severity as "error" | "warning" | "info"} />
                          </Box>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            <Chip
                              label={constraint.type.replace(/_/g, ' ').toUpperCase()}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            <Typography variant="caption" color="text.secondary">
                              Source: {constraint.source}
                            </Typography>
                          </Box>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Type
                            </Typography>
                            <Chip
                              label={constraint.type.replace(/_/g, ' ').toUpperCase()}
                              color="primary"
                              variant="outlined"
                            />
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Severity
                            </Typography>
                            <StatusBadge status={constraint.severity as "error" | "warning" | "info"} />
                          </Grid>
                          <Grid size={{ xs: 12 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Source
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {constraint.source}
                            </Typography>
                          </Grid>
                        </Grid>

                        <Divider />

                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Constraint Details
                          </Typography>
                          {Object.keys(constraint.details).length > 0 ? (
                            <CodeViewer
                              code={JSON.stringify(constraint.details, null, 2)}
                              language="json"
                            />
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              No additional details available
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            )}
          </Box>
        </TabPanel>

        {/* Validation Scripts Tab */}
        <TabPanel value={activeTab} index={2}>
          <Box sx={{ px: 3 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Validation Scripts
              </Typography>
              <Button
                variant="contained"
                startIcon={<Code />}
                onClick={handleGenerateScripts}
                disabled={isGeneratingScripts}
              >
                {isGeneratingScripts ? "Generating..." : "Generate Scripts"}
              </Button>
            </Box>

            {isLoadingScripts ? (
              <LoadingOverlay open={true} />
            ) : scripts.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <Code sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
                <Typography variant="body1" color="text.secondary" gutterBottom>
                  No validation scripts found
                </Typography>
                <Button
                  variant="outlined"
                  startIcon={<Code />}
                  onClick={handleGenerateScripts}
                  disabled={isGeneratingScripts}
                >
                  Generate Scripts
                </Button>
              </Box>
            ) : (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {scripts.map((script, index) => {
                  // Find associated constraint
                  const associatedConstraint = constraints.find(c => c.id === script.constraint_id);
                  
                  return (
                    <Accordion key={script.id} defaultExpanded={index === 0}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}>
                          <Avatar sx={{ bgcolor: "primary.main", width: 32, height: 32 }}>
                            <Code fontSize="small" />
                          </Avatar>
                          <Box sx={{ flexGrow: 1 }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {script.name}
                              </Typography>
                              <Chip
                                label={script.script_type.replace(/_/g, ' ').toUpperCase()}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            </Box>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                              {script.constraint_id && (
                                <Chip
                                  label={`Constraint: ${script.constraint_id.slice(0, 8)}...`}
                                  size="small"
                                  color="secondary"
                                  variant="outlined"
                                />
                              )}
                              <Typography variant="caption" color="text.secondary">
                                {script.description}
                              </Typography>
                            </Box>
                          </Box>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                          <Grid container spacing={2}>
                            <Grid size={{ xs: 12, sm: 6 }}>
                              <Typography variant="subtitle2" gutterBottom>
                                Script Type
                              </Typography>
                              <Chip
                                label={script.script_type.replace(/_/g, ' ').toUpperCase()}
                                color="primary"
                                variant="outlined"
                              />
                            </Grid>
                            <Grid size={{ xs: 12, sm: 6 }}>
                              <Typography variant="subtitle2" gutterBottom>
                                Associated Constraint
                              </Typography>
                              {script.constraint_id ? (
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Chip
                                    label={associatedConstraint ? associatedConstraint.description : `ID: ${script.constraint_id.slice(0, 8)}...`}
                                    size="small"
                                    color="secondary"
                                    variant="outlined"
                                  />
                                  {associatedConstraint && (
                                    <StatusBadge status={associatedConstraint.severity as "error" | "warning" | "info"} />
                                  )}
                                </Box>
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  No constraint associated
                                </Typography>
                              )}
                            </Grid>
                          </Grid>

                          <Divider />

                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              Validation Code
                            </Typography>
                            <CodeViewer
                              code={script.validation_code}
                              language="python"
                              maxHeight={300}
                            />
                          </Box>

                          {script.description && (
                            <Box>
                              <Typography variant="subtitle2" gutterBottom>
                                Description
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {script.description}
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  );
                })}
              </Box>
            )}
          </Box>
        </TabPanel>

        {/* Test Data Tab */}
        <TabPanel value={activeTab} index={3}>
          <Box sx={{ px: 3 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Test Data
              </Typography>
              <Button
                variant="contained"
                startIcon={<DataObject />}
                onClick={() => navigate(`/test-data?endpoint=${endpoint.name}`)}
              >
                Manage Test Data
              </Button>
            </Box>

            {isLoadingTestData ? (
              <LoadingOverlay open={true} />
            ) : testDataItems.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <DataObject
                  sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
                />
                <Typography variant="body1" color="text.secondary">
                  No test data found
                </Typography>
              </Box>
            ) : (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {testDataItems.map((testData, index) => (
                  <Accordion key={testData.id} defaultExpanded={index === 0}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}>
                        <Avatar sx={{ bgcolor: testData.is_valid ? "success.main" : "error.main", width: 32, height: 32 }}>
                          {testData.is_valid ? <CheckCircle fontSize="small" /> : <Error fontSize="small" />}
                        </Avatar>
                        <Box sx={{ flexGrow: 1 }}>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                              {testData.name}
                            </Typography>
                            <Chip
                              label={testData.is_valid ? "Valid" : "Invalid"}
                              size="small"
                              color={testData.is_valid ? "success" : "error"}
                            />
                          </Box>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            <Chip
                              label={`Status: ${testData.expected_status_code}`}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            {testData.description && (
                              <Typography variant="caption" color="text.secondary">
                                {testData.description}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Validation Status
                            </Typography>
                            <Chip
                              label={testData.is_valid ? "Valid" : "Invalid"}
                              color={testData.is_valid ? "success" : "error"}
                            />
                          </Grid>
                          <Grid size={{ xs: 12, sm: 6 }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Expected Status Code
                            </Typography>
                            <Chip
                              label={testData.expected_status_code}
                              color="primary"
                              variant="outlined"
                            />
                          </Grid>
                        </Grid>

                        {testData.description && (
                          <Box>
                            <Typography variant="subtitle2" gutterBottom>
                              Description
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {testData.description}
                            </Typography>
                          </Box>
                        )}

                        <Divider />

                        <Box>
                          <Typography variant="subtitle2" gutterBottom>
                            Test Data Content
                          </Typography>
                          <CodeViewer
                            code={JSON.stringify({
                              request_params: testData.request_params,
                              request_headers: testData.request_headers,
                              request_body: testData.request_body,
                              expected_response_schema: testData.expected_response_schema,
                              expected_response_contains: testData.expected_response_contains
                            }, null, 2)}
                            language="json"
                            maxHeight={300}
                          />
                        </Box>
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            )}
          </Box>
        </TabPanel>

        {/* Executions Tab */}
        <TabPanel value={activeTab} index={4}>
          <Box sx={{ px: 3 }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Execution History
              </Typography>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={() =>
                  navigate(`/executions?endpoint=${endpoint.name}`)
                }
              >
                Run Tests
              </Button>
            </Box>

            {isLoadingExecutions ? (
              <LoadingOverlay open={true} />
            ) : executions.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <PlayArrow
                  sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
                />
                <Typography variant="body1" color="text.secondary">
                  No execution history
                </Typography>
              </Box>
            ) : (
              <DataTable
                columns={[
                  {
                    key: "overall_status",
                    label: "Status",
                    render: (value: string) => <StatusBadge status={value} />,
                  },
                  { key: "total_tests", label: "Total Tests" },
                  { key: "passed_tests", label: "Passed" },
                  { key: "failed_tests", label: "Failed" },
                  {
                    key: "success_rate",
                    label: "Success Rate",
                    render: (value: number) => `${(value * 100).toFixed(1)}%`,
                  },
                  {
                    key: "started_at",
                    label: "Started At",
                    render: (value: string) => new Date(value).toLocaleString(),
                  },
                ]}
                data={executions}
                onRowClick={(execution) =>
                  navigate(`/executions/${execution.id}`)
                }
              />
            )}
          </Box>
        </TabPanel>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Endpoint"
        message={`Are you sure you want to delete "${endpoint.name}"? This will also delete all associated constraints, validation scripts, and test data. This action cannot be undone.`}
        confirmText="Delete"
        severity="error"
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialogOpen(false)}
      />
    </Box>
  );
};

export default EndpointDetailPage;
