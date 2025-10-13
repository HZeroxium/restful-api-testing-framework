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
  Tooltip,
  Tabs,
  Tab,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  ArrowBack,
  Delete,
  Api,
  Link as LinkIcon,
  CalendarToday,
  List as ListIcon,
  AccountTree,
  PlayArrow,
} from "@mui/icons-material";
import { format } from "date-fns";
import {
  useGetDatasetQuery,
  useGetDatasetEndpointsQuery,
  useDeleteDatasetMutation,
  useGetSequencesByDatasetQuery,
  useGenerateSequencesMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable } from "@/components/common/DataTable";
import type { EndpointInfo, TableColumn } from "@/types";

const DatasetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(0);
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);

  const {
    data: dataset,
    isLoading: isLoadingDataset,
    error: datasetError,
    refetch: refetchDataset,
  } = useGetDatasetQuery(id!);

  const {
    data: endpoints = [],
    isLoading: isLoadingEndpoints,
    error: endpointsError,
    refetch: refetchEndpoints,
  } = useGetDatasetEndpointsQuery(id!);

  const {
    data: sequencesData,
    isLoading: isLoadingSequences,
    error: sequencesError,
    refetch: refetchSequences,
  } = useGetSequencesByDatasetQuery({ datasetId: id!, limit: 10, offset: 0 });

  const [deleteDataset] = useDeleteDatasetMutation();
  const [generateSequences] = useGenerateSequencesMutation();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleDelete = async () => {
    try {
      await deleteDataset(id!).unwrap();
      navigate("/datasets");
    } catch (err) {
      console.error("Failed to delete dataset:", err);
    }
  };

  const handleEndpointClick = (endpoint: EndpointInfo) => {
    navigate(`/endpoints/${endpoint.id}`);
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleGenerateSequences = async () => {
    if (!id) return;

    try {
      await generateSequences({
        datasetId: id,
        body: { override_existing: true },
      }).unwrap();
      setGenerateDialogOpen(false);
      refetchSequences();
    } catch (err) {
      console.error("Failed to generate sequences:", err);
    }
  };

  const isLoading = isLoadingDataset || isLoadingEndpoints;
  const error = datasetError || endpointsError;

  if (isLoading) {
    return <LoadingOverlay open={true} />;
  }

  if (error || !dataset) {
    return (
      <ErrorAlert
        error={
          error
            ? typeof error === "object" && "message" in error
              ? error.message
              : "An error occurred"
            : "Dataset not found"
        }
        onRetry={() => {
          refetchDataset();
          refetchEndpoints();
        }}
      />
    );
  }

  const columns: TableColumn<EndpointInfo>[] = [
    {
      key: "name",
      label: "Name",
      sortable: true,
      render: (value: string) => (
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {value}
        </Typography>
      ),
    },
    {
      key: "method",
      label: "Method",
      sortable: true,
      render: (value: string) => {
        const colors: Record<
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
          <Chip
            label={value}
            size="small"
            color={colors[value] || "default"}
            sx={{ fontWeight: 600, minWidth: 70 }}
          />
        );
      },
    },
    {
      key: "path",
      label: "Path",
      sortable: true,
      render: (value: string) => (
        <Typography
          variant="body2"
          sx={{
            fontFamily: "monospace",
            fontSize: "0.875rem",
            color: "text.secondary",
          }}
        >
          {value}
        </Typography>
      ),
    },
    {
      key: "tags",
      label: "Tags",
      render: (value: string[]) => (
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {value.slice(0, 2).map((tag) => (
            <Chip key={tag} label={tag} size="small" variant="outlined" />
          ))}
          {value.length > 2 && (
            <Chip
              label={`+${value.length - 2}`}
              size="small"
              variant="outlined"
            />
          )}
        </Box>
      ),
    },
    {
      key: "auth_required",
      label: "Auth",
      sortable: true,
      render: (value: boolean, row: EndpointInfo) => (
        <Chip
          label={value ? row.auth_type || "Required" : "None"}
          size="small"
          color={value ? "warning" : "default"}
          variant="outlined"
        />
      ),
    },
  ];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate("/datasets")}
          sx={{ mb: 2 }}
        >
          Back to Datasets
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
            <Typography
              variant="h4"
              component="h1"
              sx={{ fontWeight: 600, mb: 1 }}
            >
              {dataset.name}
            </Typography>
            {dataset.description && (
              <Typography variant="body2" color="text.secondary">
                {dataset.description}
              </Typography>
            )}
          </Box>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Tooltip title="Delete Dataset">
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

      {/* Dataset Information */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                <ListIcon color="primary" />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Endpoints
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {endpoints.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                <Api color="primary" />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  OpenAPI Version
                </Typography>
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {dataset.spec_version || "N/A"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                <LinkIcon color="primary" />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Base URL
                </Typography>
              </Box>
              <Typography
                variant="body2"
                sx={{
                  fontFamily: "monospace",
                  wordBreak: "break-all",
                }}
              >
                {dataset.base_url || "Not specified"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 6, lg: 3 }}>
          <Card>
            <CardContent>
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}
              >
                <CalendarToday color="primary" />
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Created
                </Typography>
              </Box>
              <Typography variant="body2">
                {format(new Date(dataset.created_at), "MMM dd, yyyy")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {format(new Date(dataset.created_at), "HH:mm:ss")}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="dataset tabs"
          >
            <Tab icon={<ListIcon />} label="Endpoints" iconPosition="start" />
            <Tab
              icon={<AccountTree />}
              label="Operation Sequences"
              iconPosition="start"
            />
          </Tabs>
        </Box>

        {/* Tab Panels */}
        {activeTab === 0 && (
          <CardContent>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Endpoints
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {endpoints.length} endpoint{endpoints.length !== 1 ? "s" : ""}
              </Typography>
            </Box>

            {endpoints.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <ListIcon
                  sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
                />
                <Typography variant="body1" color="text.secondary">
                  No endpoints found in this dataset
                </Typography>
              </Box>
            ) : (
              <DataTable
                columns={columns}
                data={endpoints}
                onRowClick={handleEndpointClick}
              />
            )}
          </CardContent>
        )}

        {activeTab === 1 && (
          <CardContent>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                mb: 2,
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Operation Sequences
              </Typography>
              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={() => setGenerateDialogOpen(true)}
                  size="small"
                >
                  Generate
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate(`/operation-sequences?dataset=${id}`)}
                  size="small"
                >
                  View All
                </Button>
              </Box>
            </Box>

            {isLoadingSequences ? (
              <LoadingOverlay open={true} />
            ) : sequencesError ? (
              <ErrorAlert error={sequencesError.toString()} />
            ) : !sequencesData || sequencesData.sequences.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <AccountTree
                  sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
                />
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mb: 2 }}
                >
                  No operation sequences found for this dataset
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={() => setGenerateDialogOpen(true)}
                >
                  Generate Sequences
                </Button>
              </Box>
            ) : (
              <Box>
                <Grid container spacing={2}>
                  {sequencesData.sequences.slice(0, 4).map((sequence) => (
                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={sequence.id}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography
                            variant="subtitle1"
                            fontWeight="medium"
                            gutterBottom
                          >
                            {sequence.name}
                          </Typography>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mb: 2 }}
                          >
                            {sequence.description}
                          </Typography>
                          <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                            <Chip
                              label={sequence.sequence_type}
                              size="small"
                              color="primary"
                            />
                            <Chip
                              label={`${sequence.operations.length} ops`}
                              size="small"
                            />
                          </Box>
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() =>
                              navigate(`/operation-sequences/${sequence.id}`)
                            }
                            fullWidth
                          >
                            View Details
                          </Button>
                        </CardContent>
                      </Card>
                    </Grid>
                  ))}
                </Grid>
                {sequencesData.sequences.length > 4 && (
                  <Box sx={{ mt: 2, textAlign: "center" }}>
                    <Button
                      variant="text"
                      onClick={() =>
                        navigate(`/operation-sequences?dataset=${id}`)
                      }
                    >
                      View all {sequencesData.sequences.length} sequences
                    </Button>
                  </Box>
                )}
              </Box>
            )}
          </CardContent>
        )}
      </Card>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Dataset"
        message={`Are you sure you want to delete "${dataset.name}"? This will also delete all associated endpoints, constraints, and test data. This action cannot be undone.`}
        confirmText="Delete"
        severity="error"
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialogOpen(false)}
      />

      {/* Generate Sequences Dialog */}
      <ConfirmDialog
        open={generateDialogOpen}
        title="Generate Operation Sequences"
        message="This will analyze the dataset endpoints and generate operation sequences based on their dependencies. This may take a few minutes."
        confirmText="Generate"
        severity="info"
        onConfirm={handleGenerateSequences}
        onCancel={() => setGenerateDialogOpen(false)}
      />
    </Box>
  );
};

export default DatasetDetailPage;
