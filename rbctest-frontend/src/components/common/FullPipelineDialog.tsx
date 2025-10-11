import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Alert,
  LinearProgress,
  Chip,
  TextField,
  Switch,
  FormControlLabel,
  Divider,
} from "@mui/material";
import {
  CheckCircle,
  Error as ErrorIcon,
  HourglassEmpty,
} from "@mui/icons-material";
import { useRunFullPipelineMutation } from "@/services/api";
import type { FullPipelineRequest } from "@/types";

interface FullPipelineDialogProps {
  open: boolean;
  onClose: () => void;
  endpointName: string;
  defaultBaseUrl?: string;
}

const steps = [
  "Mine Constraints",
  "Generate Scripts",
  "Generate Test Data",
  "Execute Tests",
];

const FullPipelineDialog: React.FC<FullPipelineDialogProps> = ({
  open,
  onClose,
  endpointName,
  defaultBaseUrl = "",
}) => {
  const [baseUrl, setBaseUrl] = useState(defaultBaseUrl);
  const [testCount, setTestCount] = useState(5);
  const [includeInvalid, setIncludeInvalid] = useState(true);
  const [overrideExisting, setOverrideExisting] = useState(false);

  const [runFullPipeline, { isLoading, data: result, error }] =
    useRunFullPipelineMutation();

  const [activeStep, setActiveStep] = useState(-1);
  const [completedSteps, setCompletedSteps] = useState<boolean[]>([
    false,
    false,
    false,
    false,
  ]);
  const [stepErrors, setStepErrors] = useState<(string | null)[]>([
    null,
    null,
    null,
    null,
  ]);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setBaseUrl(defaultBaseUrl);
      setActiveStep(-1);
      setCompletedSteps([false, false, false, false]);
      setStepErrors([null, null, null, null]);
    }
  }, [open, defaultBaseUrl]);

  // Update progress based on result
  useEffect(() => {
    if (!result) return;

    const steps = result.step_results;
    const newCompleted = [
      steps.constraints_mining,
      steps.script_generation,
      steps.test_data_generation,
      steps.test_execution,
    ];

    setCompletedSteps(newCompleted);

    // Determine active step (first failed or last if all completed)
    const firstFailedIndex = newCompleted.findIndex((completed) => !completed);
    if (firstFailedIndex !== -1) {
      setActiveStep(firstFailedIndex);
    } else {
      setActiveStep(3); // All completed
    }
  }, [result]);

  const handleExecute = async () => {
    if (!baseUrl) return;

    setActiveStep(0);
    const request: FullPipelineRequest = {
      base_url: baseUrl,
      test_count: testCount,
      include_invalid: includeInvalid,
      override_existing: overrideExisting,
    };

    try {
      await runFullPipeline({
        endpointName,
        body: request,
      }).unwrap();
    } catch (err: any) {
      console.error("Pipeline execution failed:", err);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      onClose();
    }
  };

  const getStepIcon = (index: number) => {
    if (stepErrors[index]) {
      return <ErrorIcon color="error" />;
    }
    if (completedSteps[index]) {
      return <CheckCircle color="success" />;
    }
    if (activeStep === index) {
      return <HourglassEmpty color="primary" />;
    }
    return null;
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={isLoading}
    >
      <DialogTitle>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Full Testing Pipeline
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {endpointName}
        </Typography>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {/* Configuration */}
          {activeStep === -1 && (
            <>
              <Typography variant="body2" color="text.secondary">
                Run the complete testing pipeline: mine constraints, generate
                validation scripts, create test data, and execute tests.
              </Typography>

              <TextField
                label="Base URL"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                fullWidth
                required
                placeholder="https://api.example.com"
                disabled={isLoading}
              />

              <TextField
                label="Number of Test Cases"
                type="number"
                value={testCount}
                onChange={(e) =>
                  setTestCount(Math.max(1, parseInt(e.target.value) || 1))
                }
                fullWidth
                InputProps={{ inputProps: { min: 1, max: 50 } }}
                disabled={isLoading}
              />

              <Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={includeInvalid}
                      onChange={(e) => setIncludeInvalid(e.target.checked)}
                      disabled={isLoading}
                    />
                  }
                  label="Include Invalid Test Data"
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                >
                  Generate both valid and invalid test cases
                </Typography>
              </Box>

              <Box>
                <FormControlLabel
                  control={
                    <Switch
                      checked={overrideExisting}
                      onChange={(e) => setOverrideExisting(e.target.checked)}
                      color="warning"
                      disabled={isLoading}
                    />
                  }
                  label="Override Existing Data"
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                >
                  Delete existing constraints, scripts, and test data before
                  generation
                </Typography>
              </Box>
            </>
          )}

          {/* Progress */}
          {activeStep >= 0 && (
            <>
              <Stepper activeStep={activeStep} alternativeLabel>
                {steps.map((label, index) => (
                  <Step key={label} completed={completedSteps[index]}>
                    <StepLabel
                      error={!!stepErrors[index]}
                      StepIconComponent={() => getStepIcon(index) || <Box />}
                    >
                      {label}
                    </StepLabel>
                  </Step>
                ))}
              </Stepper>

              {isLoading && (
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Running pipeline... Please wait.
                  </Typography>
                  <LinearProgress />
                </Box>
              )}

              {error && (
                <Alert severity="error">
                  Pipeline execution failed.{" "}
                  {result?.error_message || "Please try again."}
                </Alert>
              )}

              {result && !isLoading && (
                <>
                  <Divider />

                  <Box>
                    <Typography
                      variant="subtitle2"
                      gutterBottom
                      sx={{ fontWeight: 600 }}
                    >
                      Execution Summary
                    </Typography>
                    <Box
                      sx={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 1,
                        mt: 2,
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2">Overall Status:</Typography>
                        <Chip
                          label={result.overall_success ? "Success" : "Failed"}
                          size="small"
                          color={result.overall_success ? "success" : "error"}
                        />
                      </Box>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2">
                          Total Execution Time:
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {result.total_execution_time.toFixed(2)} ms
                        </Typography>
                      </Box>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2">
                          Constraints Mined:
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {result.constraints_result.total_constraints}
                        </Typography>
                      </Box>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2">
                          Scripts Generated:
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {result.scripts_result.total_scripts}
                        </Typography>
                      </Box>

                      <Box
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <Typography variant="body2">
                          Test Data Created:
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {result.test_data_result?.total_count || 0}
                        </Typography>
                      </Box>

                      {result.execution_result && (
                        <>
                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <Typography variant="body2">
                              Tests Passed:
                            </Typography>
                            <Chip
                              label={result.execution_result.passed_tests}
                              size="small"
                              color="success"
                            />
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <Typography variant="body2">
                              Tests Failed:
                            </Typography>
                            <Chip
                              label={result.execution_result.failed_tests}
                              size="small"
                              color="error"
                            />
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <Typography variant="body2">
                              Success Rate:
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 500 }}
                            >
                              {(
                                result.execution_result.success_rate * 100
                              ).toFixed(1)}
                              %
                            </Typography>
                          </Box>
                        </>
                      )}
                    </Box>
                  </Box>

                  {result.overall_success && (
                    <Alert severity="success" icon={<CheckCircle />}>
                      Full pipeline executed successfully!
                    </Alert>
                  )}
                </>
              )}
            </>
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={isLoading}>
          {result ? "Close" : "Cancel"}
        </Button>
        {activeStep === -1 && (
          <Button
            onClick={handleExecute}
            variant="contained"
            disabled={!baseUrl || isLoading}
          >
            Run Pipeline
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default FullPipelineDialog;
