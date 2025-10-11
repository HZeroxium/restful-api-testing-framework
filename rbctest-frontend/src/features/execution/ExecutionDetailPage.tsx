import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Alert,
  Switch,
  FormControlLabel,
} from "@mui/material";
import {
  ArrowBack,
  ExpandMore,
  CheckCircle,
  Error as ErrorIcon,
  AccessTime,
  Refresh,
} from "@mui/icons-material";
import { format } from "date-fns";
import {
  useGetExecutionDetailsQuery,
  useDeleteExecutionMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { CodeViewer } from "@/components/common/CodeViewer";
import { StatusBadge } from "@/components/common/StatusBadge";

const ExecutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [expandedResult, setExpandedResult] = useState<string | false>(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const {
    data: execution,
    isLoading,
    error,
    refetch,
  } = useGetExecutionDetailsQuery(id!, {
    pollingInterval: autoRefresh ? 5000 : 0, // Poll every 5 seconds if auto-refresh is on
  });

  const [deleteExecution] = useDeleteExecutionMutation();

  // Auto-refresh for running executions
  useEffect(() => {
    if (
      execution?.overall_status === "running" ||
      execution?.overall_status === "pending"
    ) {
      setAutoRefresh(true);
    }
  }, [execution?.overall_status]);

  const handleDelete = async () => {
    try {
      await deleteExecution(id!).unwrap();
      navigate("/executions");
    } catch (err) {
      console.error("Failed to delete execution:", err);
    }
  };

  const handleAccordionChange =
    (resultId: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedResult(isExpanded ? resultId : false);
    };

  if (isLoading) {
    return <LoadingOverlay open={true} />;
  }

  if (error || !execution) {
    return (
      <ErrorAlert
        error={
          error
            ? typeof error === "object" && "message" in error
              ? error.message
              : "An error occurred"
            : "Execution not found"
        }
        onRetry={refetch}
      />
    );
  }

  const isRunning =
    execution.overall_status === "running" ||
    execution.overall_status === "pending";

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate("/executions")}
          sx={{ mb: 2 }}
        >
          Back to Executions
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
                Execution Details
              </Typography>
              <StatusBadge status={execution.overall_status} />
            </Box>
            <Typography variant="body1" sx={{ mb: 0.5 }}>
              <strong>Endpoint:</strong> {execution.endpoint_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <strong>Base URL:</strong> {execution.base_url}
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
              }
              label="Auto-refresh"
            />
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
          </Box>
        </Box>
      </Box>

      {/* Status Alert */}
      {isRunning && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Execution is currently {execution.overall_status}. Auto-refresh is
          enabled.
        </Alert>
      )}

      {execution.error_message && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {execution.error_message}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Total Tests
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {execution.total_tests}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
              >
                <CheckCircle color="success" />
                <Typography variant="subtitle2" color="text.secondary">
                  Passed
                </Typography>
              </Box>
              <Typography
                variant="h4"
                sx={{ fontWeight: 700, color: "success.main" }}
              >
                {execution.passed_tests}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
              >
                <ErrorIcon color="error" />
                <Typography variant="subtitle2" color="text.secondary">
                  Failed
                </Typography>
              </Box>
              <Typography
                variant="h4"
                sx={{ fontWeight: 700, color: "error.main" }}
              >
                {execution.failed_tests}
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
                Success Rate
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {(execution.success_rate * 100).toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Execution Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Execution Information
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Box>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Started At
                </Typography>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <AccessTime fontSize="small" color="action" />
                  <Typography variant="body2">
                    {format(
                      new Date(execution.started_at),
                      "MMM dd, yyyy HH:mm:ss"
                    )}
                  </Typography>
                </Box>
              </Box>
            </Grid>
            {execution.completed_at && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <Box>
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Completed At
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <AccessTime fontSize="small" color="action" />
                    <Typography variant="body2">
                      {format(
                        new Date(execution.completed_at),
                        "MMM dd, yyyy HH:mm:ss"
                      )}
                    </Typography>
                  </Box>
                </Box>
              </Grid>
            )}
            <Grid size={{ xs: 12, sm: 6 }}>
              <Box>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Total Execution Time
                </Typography>
                <Typography variant="body2">
                  {execution.total_execution_time_ms.toFixed(2)} ms
                </Typography>
              </Box>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Box>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Test Data Used
                </Typography>
                <Typography variant="body2">
                  {execution.test_data_used.length} test case
                  {execution.test_data_used.length !== 1 ? "s" : ""}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Test Results */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Test Results
          </Typography>

          {execution.execution_results.length === 0 ? (
            <Alert severity="info">No test results available</Alert>
          ) : (
            <Box
              sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 2 }}
            >
              {execution.execution_results.map((result, index) => (
                <Accordion
                  key={index}
                  expanded={expandedResult === `result-${index}`}
                  onChange={handleAccordionChange(`result-${index}`)}
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
                      {result.passed ? (
                        <CheckCircle color="success" />
                      ) : (
                        <ErrorIcon color="error" />
                      )}
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography
                          variant="subtitle2"
                          sx={{ fontWeight: 600 }}
                        >
                          {result.test_data_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Execution Time: {result.execution_time_ms.toFixed(2)}{" "}
                          ms
                        </Typography>
                      </Box>
                      <Chip
                        label={result.execution_status}
                        size="small"
                        color={result.passed ? "success" : "error"}
                      />
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box
                      sx={{ display: "flex", flexDirection: "column", gap: 3 }}
                    >
                      {result.error_message && (
                        <Alert severity="error">{result.error_message}</Alert>
                      )}

                      <Box>
                        <Typography
                          variant="subtitle2"
                          gutterBottom
                          sx={{ fontWeight: 600 }}
                        >
                          Request Sent
                        </Typography>
                        <CodeViewer
                          code={JSON.stringify(result.request_sent, null, 2)}
                          language="json"
                        />
                      </Box>

                      <Divider />

                      <Box>
                        <Typography
                          variant="subtitle2"
                          gutterBottom
                          sx={{ fontWeight: 600 }}
                        >
                          Response Received
                        </Typography>
                        <CodeViewer
                          code={JSON.stringify(
                            result.response_received,
                            null,
                            2
                          )}
                          language="json"
                        />
                      </Box>

                      {result.validation_results.length > 0 && (
                        <>
                          <Divider />
                          <Box>
                            <Typography
                              variant="subtitle2"
                              gutterBottom
                              sx={{ fontWeight: 600 }}
                            >
                              Validation Results
                            </Typography>
                            {result.validation_results.map(
                              (validation, vIndex) => (
                                <Card
                                  key={vIndex}
                                  variant="outlined"
                                  sx={{ mt: 1 }}
                                >
                                  <CardContent>
                                    <CodeViewer
                                      code={JSON.stringify(validation, null, 2)}
                                      language="json"
                                    />
                                  </CardContent>
                                </Card>
                              )
                            )}
                          </Box>
                        </>
                      )}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Execution"
        message="Are you sure you want to delete this execution? This action cannot be undone."
        confirmText="Delete"
        severity="error"
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialogOpen(false)}
      />
    </Box>
  );
};

export default ExecutionDetailPage;
