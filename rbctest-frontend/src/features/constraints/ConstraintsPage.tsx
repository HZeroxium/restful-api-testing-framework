import React, { useState, useEffect } from "react";
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
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Grid,
  Divider,
  TablePagination,
} from "@mui/material";
import { Search, BugReport, FilterList, ExpandMore } from "@mui/icons-material";
import {
  useGetConstraintsQuery,
  useMineConstraintsByEndpointNameMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CodeViewer } from "@/components/common/CodeViewer";
import EndpointAutocomplete from "@/components/common/EndpointAutocomplete";
import { usePagination } from "@/hooks/usePagination";

const ConstraintsPage: React.FC = () => {
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
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [mineDialogOpen, setMineDialogOpen] = useState(false);
  const [selectedEndpointName, setSelectedEndpointName] = useState("");
  const [expandedConstraint, setExpandedConstraint] = useState<string | false>(
    false
  );

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination();
  }, [searchTerm, typeFilter, severityFilter, resetPagination]);

  const {
    data: constraintsData,
    isLoading,
    error,
    refetch,
  } = useGetConstraintsQuery({ limit, offset });
  const [mineConstraints, { isLoading: isMining, error: mineError }] =
    useMineConstraintsByEndpointNameMutation();

  const constraints = constraintsData?.constraints || [];

  // Check if client-side filtering is active
  const hasActiveFilters =
    searchTerm !== "" || typeFilter !== "all" || severityFilter !== "all";

  // Filter constraints (only when filters are active)
  const filteredConstraints = hasActiveFilters
    ? constraints.filter((constraint) => {
        const matchesSearch =
          searchTerm === "" ||
          constraint.description
            .toLowerCase()
            .includes(searchTerm.toLowerCase()) ||
          constraint.type.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesType =
          typeFilter === "all" || constraint.type === typeFilter;
        const matchesSeverity =
          severityFilter === "all" || constraint.severity === severityFilter;

        return matchesSearch && matchesType && matchesSeverity;
      })
    : constraints;

  const handleMineConstraints = async () => {
    if (!selectedEndpointName) return;

    try {
      await mineConstraints(selectedEndpointName).unwrap();
      setMineDialogOpen(false);
      setSelectedEndpointName("");
      refetch();
    } catch (err) {
      console.error("Failed to mine constraints:", err);
    }
  };

  const handleAccordionChange =
    (constraintId: string) =>
    (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedConstraint(isExpanded ? constraintId : false);
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
              Constraints
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View and manage API constraints
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<BugReport />}
            onClick={() => setMineDialogOpen(true)}
          >
            Mine Constraints
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
              placeholder="Search constraints..."
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
              <InputLabel>Type</InputLabel>
              <Select
                value={typeFilter}
                label="Type"
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="request_param">Request Param</MenuItem>
                <MenuItem value="request_body">Request Body</MenuItem>
                <MenuItem value="response_property">Response Property</MenuItem>
                <MenuItem value="request_response">Request-Response</MenuItem>
              </Select>
            </FormControl>

            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Severity</InputLabel>
              <Select
                value={severityFilter}
                label="Severity"
                onChange={(e) => setSeverityFilter(e.target.value)}
              >
                <MenuItem value="all">All Severities</MenuItem>
                <MenuItem value="error">Error</MenuItem>
                <MenuItem value="warning">Warning</MenuItem>
                <MenuItem value="info">Info</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterList fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {filteredConstraints.length} of {constraints.length} constraints
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Constraints Table */}
      <Card>
        <CardContent>
          {filteredConstraints.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 6 }}>
              <BugReport
                sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
              />
              <Typography variant="h6" gutterBottom>
                No constraints found
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {constraints.length === 0
                  ? "Mine constraints from your endpoints to get started"
                  : "Try adjusting your filters"}
              </Typography>
              {constraints.length === 0 && (
                <Button
                  variant="outlined"
                  startIcon={<BugReport />}
                  onClick={() => setMineDialogOpen(true)}
                >
                  Mine Constraints
                </Button>
              )}
            </Box>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {filteredConstraints.map((constraint) => (
                <Accordion
                  key={constraint.id}
                  expanded={expandedConstraint === constraint.id}
                  onChange={handleAccordionChange(constraint.id)}
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
                      <BugReport color="primary" />
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
                            {constraint.description}
                          </Typography>
                          <StatusBadge
                            status={
                              constraint.severity as
                                | "error"
                                | "warning"
                                | "info"
                            }
                          />
                        </Box>
                        <Box
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <Chip
                            label={constraint.type
                              .replace(/_/g, " ")
                              .toUpperCase()}
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
                    <Box
                      sx={{ display: "flex", flexDirection: "column", gap: 2 }}
                    >
                      <Grid container spacing={2}>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Type
                          </Typography>
                          <Chip
                            label={constraint.type
                              .replace(/_/g, " ")
                              .toUpperCase()}
                            color="primary"
                            variant="outlined"
                          />
                        </Grid>
                        <Grid size={{ xs: 12, sm: 6 }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Severity
                          </Typography>
                          <StatusBadge
                            status={
                              constraint.severity as
                                | "error"
                                | "warning"
                                | "info"
                            }
                          />
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

          {/* Pagination */}
          {!hasActiveFilters && (
            <TablePagination
              component="div"
              count={constraintsData?.pagination.total_items || 0}
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

      {/* Mine Constraints Dialog */}
      <Dialog
        open={mineDialogOpen}
        onClose={() => setMineDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Mine Constraints</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select an endpoint to automatically mine constraints from its
              schema and documentation.
            </Typography>

            {mineError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                Failed to mine constraints. Please try again.
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
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMineDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleMineConstraints}
            variant="contained"
            disabled={!selectedEndpointName || isMining}
          >
            {isMining ? "Mining..." : "Mine Constraints"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConstraintsPage;
