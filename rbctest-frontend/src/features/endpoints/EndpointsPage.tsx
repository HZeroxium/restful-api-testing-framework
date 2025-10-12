import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Chip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Menu,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import {
  Search,
  FilterList,
  Api,
  MoreVert,
  Delete,
  Clear,
} from "@mui/icons-material";
import {
  useGetEndpointsQuery,
  useCleanupEndpointArtifactsMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { DataTable } from "@/components/common/DataTable";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { usePagination } from "@/hooks/usePagination";
import type { EndpointResponse, TableColumn } from "@/types";

const EndpointsPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    page,
    pageSize,
    offset,
    limit,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  } = usePagination({ defaultPageSize: 10 });
  const [searchTerm, setSearchTerm] = useState("");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedEndpoint, setSelectedEndpoint] =
    useState<EndpointResponse | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [cleanupType, setCleanupType] = useState<string>("");

  const [cleanupEndpointArtifacts] = useCleanupEndpointArtifactsMutation();

  const { data, isLoading, error, refetch } = useGetEndpointsQuery({
    limit,
    offset,
  });

  const endpoints = data?.endpoints || [];

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination();
  }, [searchTerm, methodFilter, resetPagination]);

  // Check if client-side filtering is active
  const hasActiveFilters = searchTerm !== "" || methodFilter !== "all";

  // Filter endpoints based on search and method (only when filters are active)
  const filteredEndpoints = hasActiveFilters
    ? endpoints.filter((endpoint) => {
        const matchesSearch =
          searchTerm === "" ||
          endpoint.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          endpoint.path.toLowerCase().includes(searchTerm.toLowerCase()) ||
          endpoint.tags.some((tag) =>
            tag.toLowerCase().includes(searchTerm.toLowerCase())
          );

        const matchesMethod =
          methodFilter === "all" || endpoint.method === methodFilter;

        return matchesSearch && matchesMethod;
      })
    : endpoints;

  const handleEndpointClick = (endpoint: EndpointResponse) => {
    navigate(`/endpoints/${endpoint.id}`);
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    endpoint: EndpointResponse
  ) => {
    setAnchorEl(event.currentTarget);
    setSelectedEndpoint(endpoint);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedEndpoint(null);
  };

  const handleCleanupAction = (type: string) => {
    setCleanupType(type);
    setShowConfirmDialog(true);
    handleMenuClose();
  };

  const handleConfirmCleanup = async () => {
    if (!selectedEndpoint) return;

    try {
      await cleanupEndpointArtifacts(selectedEndpoint.name).unwrap();
      setShowConfirmDialog(false);
      setCleanupType("");
      // Optionally show success message or refresh data
    } catch (error) {
      console.error("Cleanup failed:", error);
      // Optionally show error message
    }
  };

  const columns: TableColumn<EndpointResponse>[] = [
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
      render: (value: boolean, row: EndpointResponse) => (
        <Chip
          label={value ? row.auth_type || "Required" : "None"}
          size="small"
          color={value ? "warning" : "default"}
          variant="outlined"
        />
      ),
    },
    {
      key: "description",
      label: "Description",
      render: (value?: string) => (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            maxWidth: 300,
          }}
        >
          {value || "-"}
        </Typography>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (_, row: EndpointResponse) => (
        <IconButton size="small" onClick={(e) => handleMenuOpen(e, row)}>
          <MoreVert />
        </IconButton>
      ),
    },
  ];

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
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
          Endpoints
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Browse and manage API endpoints
        </Typography>
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
              placeholder="Search endpoints..."
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
              <InputLabel>Method</InputLabel>
              <Select
                value={methodFilter}
                label="Method"
                onChange={(e) => setMethodFilter(e.target.value)}
              >
                <MenuItem value="all">All Methods</MenuItem>
                <MenuItem value="GET">GET</MenuItem>
                <MenuItem value="POST">POST</MenuItem>
                <MenuItem value="PUT">PUT</MenuItem>
                <MenuItem value="PATCH">PATCH</MenuItem>
                <MenuItem value="DELETE">DELETE</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterList fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {filteredEndpoints.length} of {endpoints.length} endpoints
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Endpoints Table */}
      <Card>
        <CardContent>
          {filteredEndpoints.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Api sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No endpoints found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {endpoints.length === 0
                  ? "Upload an OpenAPI specification to get started"
                  : "Try adjusting your filters"}
              </Typography>
            </Box>
          ) : (
            <DataTable
              columns={columns}
              data={filteredEndpoints}
              onRowClick={handleEndpointClick}
              page={hasActiveFilters ? 0 : page}
              pageSize={hasActiveFilters ? filteredEndpoints.length : pageSize}
              totalCount={
                hasActiveFilters
                  ? filteredEndpoints.length
                  : data?.pagination.total_items || 0
              }
              onPageChange={
                hasActiveFilters
                  ? () => {}
                  : (page: number) => handlePageChange(undefined, page)
              }
              onPageSizeChange={
                hasActiveFilters
                  ? () => {}
                  : (pageSize: number) =>
                      handlePageSizeChange({
                        target: { value: pageSize.toString() },
                      } as React.ChangeEvent<HTMLInputElement>)
              }
            />
          )}
        </CardContent>
      </Card>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => handleCleanupAction("artifacts")}>
          <ListItemIcon>
            <Delete fontSize="small" />
          </ListItemIcon>
          <ListItemText>Clean All Artifacts</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleCleanupAction("constraints")}>
          <ListItemIcon>
            <Clear fontSize="small" />
          </ListItemIcon>
          <ListItemText>Clean Constraints Only</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleCleanupAction("test-data")}>
          <ListItemIcon>
            <Clear fontSize="small" />
          </ListItemIcon>
          <ListItemText>Clean Test Data Only</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleCleanupAction("executions")}>
          <ListItemIcon>
            <Clear fontSize="small" />
          </ListItemIcon>
          <ListItemText>Clean Executions Only</ListItemText>
        </MenuItem>
      </Menu>

      {/* Confirm Dialog */}
      <ConfirmDialog
        open={showConfirmDialog}
        onCancel={() => setShowConfirmDialog(false)}
        onConfirm={handleConfirmCleanup}
        title={`Clean ${
          cleanupType === "artifacts"
            ? "All Artifacts"
            : cleanupType.replace("-", " ")
        }`}
        message={`Are you sure you want to clean ${
          cleanupType === "artifacts"
            ? "all artifacts"
            : cleanupType.replace("-", " ")
        } for endpoint "${
          selectedEndpoint?.name
        }"? This action cannot be undone.`}
        severity="warning"
      />
    </Box>
  );
};

export default EndpointsPage;
