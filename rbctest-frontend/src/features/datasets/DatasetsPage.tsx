import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from "@mui/material";
import {
  Add,
  MoreVert,
  FolderOpen,
  Delete,
  Edit,
  Api,
  CalendarToday,
} from "@mui/icons-material";
import { format } from "date-fns";
import {
  useGetDatasetsQuery,
  useDeleteDatasetMutation,
  useCreateDatasetMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import type { Dataset, CreateDatasetRequest } from "@/types";

const DatasetsPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    data: datasets = [],
    isLoading,
    error,
    refetch,
  } = useGetDatasetsQuery();
  const [deleteDataset] = useDeleteDatasetMutation();
  const [createDataset] = useCreateDatasetMutation();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newDatasetName, setNewDatasetName] = useState("");
  const [newDatasetDescription, setNewDatasetDescription] = useState("");

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    dataset: Dataset
  ) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedDataset(dataset);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleDelete = async () => {
    if (selectedDataset) {
      try {
        await deleteDataset(selectedDataset.id).unwrap();
        setDeleteDialogOpen(false);
        handleMenuClose();
      } catch (err) {
        console.error("Failed to delete dataset:", err);
      }
    }
  };

  const handleCreate = async () => {
    if (!newDatasetName.trim()) return;

    try {
      const request: CreateDatasetRequest = {
        name: newDatasetName.trim(),
        ...(newDatasetDescription.trim() && {
          description: newDatasetDescription.trim(),
        }),
      };
      await createDataset(request).unwrap();
      setCreateDialogOpen(false);
      setNewDatasetName("");
      setNewDatasetDescription("");
    } catch (err) {
      console.error("Failed to create dataset:", err);
    }
  };

  const handleCardClick = (datasetId: string) => {
    navigate(`/datasets/${datasetId}`);
  };

  if (isLoading) {
    return <LoadingOverlay open={true} />;
  }

  if (error) {
    return (
      <ErrorAlert
        error={
          error
            ? typeof error === "object" && "message" in error
              ? error.message
              : "An error occurred"
            : "An error occurred"
        }
        onRetry={refetch}
      />
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
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
            Datasets
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage your API datasets and specifications
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Add />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Dataset
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => navigate("/datasets/upload")}
          >
            Upload Spec
          </Button>
        </Box>
      </Box>

      {/* Empty State */}
      {datasets.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: "center", py: 6 }}>
            <FolderOpen sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No datasets yet
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Get started by creating a new dataset or uploading an OpenAPI
              specification
            </Typography>
            <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
              <Button
                variant="outlined"
                startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create Dataset
              </Button>
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => navigate("/datasets/upload")}
              >
                Upload Spec
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {datasets.map((dataset) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={dataset.id}>
              <Card
                sx={{
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: "elevated",
                  },
                }}
                onClick={() => handleCardClick(dataset.id)}
              >
                <CardContent>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      mb: 2,
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <FolderOpen color="primary" />
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {dataset.name}
                      </Typography>
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuOpen(e, dataset)}
                      sx={{ mt: -1 }}
                    >
                      <MoreVert />
                    </IconButton>
                  </Box>

                  {dataset.description && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 2,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        minHeight: "2.5em",
                      }}
                    >
                      {dataset.description}
                    </Typography>
                  )}

                  <Box
                    sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2 }}
                  >
                    {dataset.spec_version && (
                      <Chip
                        label={`OpenAPI ${dataset.spec_version}`}
                        size="small"
                        variant="outlined"
                        icon={<Api />}
                      />
                    )}
                    {dataset.base_url && (
                      <Chip
                        label="Has Base URL"
                        size="small"
                        color="success"
                        variant="outlined"
                      />
                    )}
                  </Box>

                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                    <CalendarToday
                      sx={{ fontSize: 14, color: "text.secondary" }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      Created{" "}
                      {format(new Date(dataset.created_at), "MMM dd, yyyy")}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            if (selectedDataset) {
              navigate(`/datasets/${selectedDataset.id}`);
            }
            handleMenuClose();
          }}
        >
          <Edit sx={{ mr: 1, fontSize: 20 }} />
          View Details
        </MenuItem>
        <MenuItem
          onClick={() => {
            setDeleteDialogOpen(true);
            handleMenuClose();
          }}
          sx={{ color: "error.main" }}
        >
          <Delete sx={{ mr: 1, fontSize: 20 }} />
          Delete
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Dataset"
        message={`Are you sure you want to delete "${selectedDataset?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        severity="error"
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialogOpen(false)}
      />

      {/* Create Dataset Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Dataset</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="Dataset Name"
              value={newDatasetName}
              onChange={(e) => setNewDatasetName(e.target.value)}
              fullWidth
              required
              autoFocus
            />
            <TextField
              label="Description"
              value={newDatasetDescription}
              onChange={(e) => setNewDatasetDescription(e.target.value)}
              fullWidth
              multiline
              rows={3}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!newDatasetName.trim()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DatasetsPage;
