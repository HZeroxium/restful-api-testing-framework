import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  ArrowBack,
  Edit,
  Delete,
  PlayArrow,
  ExpandMore,
  CheckCircle,
  Error,
} from "@mui/icons-material";
import {
  useGetSequenceByIdQuery,
  useUpdateSequenceMutation,
  useDeleteSequenceMutation,
  useValidateSequenceMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import ReactFlowGraph from "@/components/graphs/ReactFlowGraph";
import ThreeJsGraph from "@/components/graphs/ThreeJsGraph";
import type { UpdateSequenceRequest } from "@/types";
import { sequenceToDependencyGraph } from "@/utils/operationSequence.mappers";

const OperationSequenceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [graphType, setGraphType] = useState<"2d" | "3d">("3d");
  const [vizFullScreen, setVizFullScreen] = useState(false);

  const [editForm, setEditForm] = useState<UpdateSequenceRequest>({});

  const {
    data: sequence,
    isLoading,
    error,
    refetch,
  } = useGetSequenceByIdQuery(id!);

  const [updateSequence, { isLoading: isUpdating }] =
    useUpdateSequenceMutation();
  const [deleteSequence, { isLoading: isDeleting }] =
    useDeleteSequenceMutation();
  const [
    validateSequence,
    { data: validationResult, isLoading: isValidating },
  ] = useValidateSequenceMutation();

  const handleEdit = () => {
    if (sequence) {
      setEditForm({
        name: sequence.name,
        description: sequence.description,
        sequence_type: sequence.sequence_type,
        priority: sequence.priority,
        estimated_duration: sequence.estimated_duration ?? undefined,
      });
      setEditDialogOpen(true);
    }
  };

  const handleSaveEdit = async () => {
    if (!id) return;

    try {
      await updateSequence({
        sequenceId: id,
        body: editForm,
      }).unwrap();
      setEditDialogOpen(false);
      refetch();
    } catch (err) {
      console.error("Failed to update sequence:", err);
    }
  };

  const handleDelete = async () => {
    if (!id) return;

    try {
      await deleteSequence(id).unwrap();
      navigate("/operation-sequences");
    } catch (err) {
      console.error("Failed to delete sequence:", err);
    }
  };

  const handleValidate = async () => {
    if (!sequence) return;

    try {
      await validateSequence(sequence).unwrap();
      setValidationDialogOpen(true);
    } catch (err) {
      console.error("Failed to validate sequence:", err);
    }
  };

  if (isLoading) {
    return <LoadingOverlay open={true} />;
  }

  if (error || !sequence) {
    return (
      <ErrorAlert
        error={
          error
            ? typeof error === "object" && "message" in error
              ? error.message
              : "An error occurred"
            : "Sequence not found"
        }
        onRetry={() => refetch()}
      />
    );
  }

  const graphData = sequenceToDependencyGraph(sequence);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
        <IconButton
          onClick={() => navigate("/operation-sequences")}
          sx={{ mr: 1 }}
        >
          <ArrowBack />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" gutterBottom>
            {sequence.name}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {sequence.description}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<PlayArrow />}
            onClick={handleValidate}
            disabled={isValidating}
          >
            Validate
          </Button>
          <Button variant="outlined" startIcon={<Edit />} onClick={handleEdit}>
            Edit
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Delete />}
            onClick={() => setDeleteDialogOpen(true)}
            disabled={isDeleting}
          >
            Delete
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Sequence Info */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sequence Information
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Type
                  </Typography>
                  <Chip
                    label={sequence.sequence_type}
                    color="primary"
                    size="small"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Priority
                  </Typography>
                  <Typography variant="body2">
                    {sequence.priority === 1
                      ? "High"
                      : sequence.priority === 2
                      ? "Medium"
                      : "Low"}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Estimated Duration
                  </Typography>
                  <Typography variant="body2">
                    {sequence.estimated_duration
                      ? `${sequence.estimated_duration.toFixed(1)}s`
                      : "Not specified"}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Operations Count
                  </Typography>
                  <Typography variant="body2">
                    {sequence.operations.length} operations
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Operations List */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Operations ({sequence.operations.length})
              </Typography>
              <List>
                {sequence.operations.map((operation, index) => (
                  <React.Fragment key={index}>
                    <ListItem>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Chip
                              label={operation.split(" ")[0]}
                              size="small"
                              color={
                                operation.startsWith("GET")
                                  ? "primary"
                                  : "secondary"
                              }
                            />
                            <Typography variant="body2">{operation}</Typography>
                          </Box>
                        }
                        secondary={`Step ${index + 1}`}
                      />
                      <ListItemSecondaryAction>
                        <Typography variant="caption" color="text.secondary">
                          #{index + 1}
                        </Typography>
                      </ListItemSecondaryAction>
                    </ListItem>
                    {index < sequence.operations.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>

          {/* Dependencies */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dependencies ({sequence.dependencies.length})
              </Typography>
              {sequence.dependencies.length === 0 ? (
                <Alert severity="info">
                  No dependencies defined for this sequence.
                </Alert>
              ) : (
                <List>
                  {sequence.dependencies.map((dependency, index) => (
                    <Accordion key={index}>
                      <AccordionSummary expandIcon={<ExpandMore />}>
                        <Typography variant="subtitle2">
                          {dependency.source_operation} →{" "}
                          {dependency.target_operation}
                        </Typography>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          <strong>Reason:</strong> {dependency.reason}
                        </Typography>
                        {Object.keys(dependency.data_mapping).length > 0 && (
                          <Typography variant="body2">
                            <strong>Data Mapping:</strong>{" "}
                            {JSON.stringify(dependency.data_mapping)}
                          </Typography>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Visualization */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  mb: 1,
                }}
              >
                <Typography variant="h6">Dependency Graph</Typography>
                <Box sx={{ display: "flex", gap: 1 }}>
                  <Button
                    variant={graphType === "2d" ? "contained" : "outlined"}
                    size="small"
                    onClick={() => setGraphType("2d")}
                  >
                    2D
                  </Button>
                  <Button
                    variant={graphType === "3d" ? "contained" : "outlined"}
                    size="small"
                    onClick={() => setGraphType("3d")}
                  >
                    3D
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => setVizFullScreen(true)}
                  >
                    Fullscreen
                  </Button>
                </Box>
              </Box>

              {graphType === "2d" ? (
                <ReactFlowGraph
                  graphData={graphData}
                  onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
                  autoLayout="grid"
                />
              ) : (
                <ThreeJsGraph
                  graphData={graphData}
                  onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
                />
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Fullscreen Visualization Dialog */}
      <Dialog
        open={vizFullScreen}
        onClose={() => setVizFullScreen(false)}
        fullScreen
      >
        <Box
          sx={{
            p: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6">Dependency Graph</Typography>
          <Button variant="outlined" onClick={() => setVizFullScreen(false)}>
            Close
          </Button>
        </Box>
        <Box sx={{ p: 2 }}>
          {graphType === "2d" ? (
            <ReactFlowGraph
              graphData={graphData}
              onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
              autoLayout="grid"
            />
          ) : (
            <ThreeJsGraph
              graphData={graphData}
              onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
            />
          )}
        </Box>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Sequence</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
            <TextField
              label="Name"
              value={editForm.name || ""}
              onChange={(e) =>
                setEditForm({ ...editForm, name: e.target.value })
              }
              fullWidth
            />
            <TextField
              label="Description"
              value={editForm.description || ""}
              onChange={(e) =>
                setEditForm({ ...editForm, description: e.target.value })
              }
              fullWidth
              multiline
              rows={3}
            />
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={editForm.sequence_type || ""}
                label="Type"
                onChange={(e) =>
                  setEditForm({ ...editForm, sequence_type: e.target.value })
                }
              >
                <MenuItem value="workflow">Workflow</MenuItem>
                <MenuItem value="crud">CRUD</MenuItem>
                <MenuItem value="data_flow">Data Flow</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={editForm.priority || 1}
                label="Priority"
                onChange={(e) =>
                  setEditForm({
                    ...editForm,
                    priority: parseInt(String(e.target.value)),
                  })
                }
              >
                <MenuItem value={1}>High</MenuItem>
                <MenuItem value={2}>Medium</MenuItem>
                <MenuItem value={3}>Low</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Estimated Duration (seconds)"
              type="number"
              value={editForm.estimated_duration || ""}
              onChange={(e) =>
                setEditForm({
                  ...editForm,
                  estimated_duration: parseFloat(e.target.value),
                })
              }
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveEdit}
            variant="contained"
            disabled={isUpdating}
          >
            {isUpdating ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Validation Dialog */}
      <Dialog
        open={validationDialogOpen}
        onClose={() => setValidationDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Validation Results</DialogTitle>
        <DialogContent>
          {validationResult && (
            <Box sx={{ pt: 2 }}>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                {validationResult.is_valid ? (
                  <CheckCircle color="success" />
                ) : (
                  <Error color="error" />
                )}
                <Typography variant="h6">
                  {validationResult.is_valid ? "Valid" : "Invalid"}
                </Typography>
              </Box>

              {validationResult.errors.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="error" gutterBottom>
                    Errors:
                  </Typography>
                  {validationResult.errors.map((error, index) => (
                    <Alert key={index} severity="error" sx={{ mb: 1 }}>
                      {error}
                    </Alert>
                  ))}
                </Box>
              )}

              {validationResult.warnings.length > 0 && (
                <Box>
                  <Typography
                    variant="subtitle2"
                    color="warning.main"
                    gutterBottom
                  >
                    Warnings:
                  </Typography>
                  {validationResult.warnings.map((warning, index) => (
                    <Alert key={index} severity="warning" sx={{ mb: 1 }}>
                      {warning}
                    </Alert>
                  ))}
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setValidationDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onCancel={() => setDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        title="Delete Sequence"
        message={`Are you sure you want to delete "${sequence.name}"? This action cannot be undone.`}
        severity="warning"
      />
    </Box>
  );
};

export default OperationSequenceDetailPage;
