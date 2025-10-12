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
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Grid,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TablePagination,
} from "@mui/material";
import {
  Search,
  Code,
  FilterList,
  ExpandMore,
  Download,
} from "@mui/icons-material";
import {
  useGetScriptsQuery,
  useGenerateScriptsByEndpointNameMutation,
  useExportToPythonFileMutation,
} from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { CodeViewer } from "@/components/common/CodeViewer";
import EndpointAutocomplete from "@/components/common/EndpointAutocomplete";
import { usePagination } from "@/hooks/usePagination";

const ValidationScriptsPage: React.FC = () => {
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
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [selectedEndpointName, setSelectedEndpointName] = useState("");
  const [expandedScript, setExpandedScript] = useState<string | false>(false);

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination();
  }, [searchTerm, typeFilter, resetPagination]);

  const {
    data: scriptsData,
    isLoading,
    error,
    refetch,
  } = useGetScriptsQuery({ limit, offset });
  // Endpoints are fetched by EndpointAutocomplete component
  const [generateScripts, { isLoading: isGenerating, error: generateError }] =
    useGenerateScriptsByEndpointNameMutation();
  const [exportScripts, { isLoading: isExporting, error: exportError }] =
    useExportToPythonFileMutation();

  const scripts = scriptsData?.scripts || [];
  // Endpoints are fetched by EndpointAutocomplete component

  // Check if client-side filtering is active
  const hasActiveFilters = searchTerm !== "" || typeFilter !== "all";

  // Filter scripts (only when filters are active)
  const filteredScripts = hasActiveFilters
    ? scripts.filter((script) => {
        const matchesSearch =
          searchTerm === "" ||
          script.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          script.description.toLowerCase().includes(searchTerm.toLowerCase());

        const matchesType =
          typeFilter === "all" || script.script_type === typeFilter;

        return matchesSearch && matchesType;
      })
    : scripts;

  const handleGenerateScripts = async () => {
    if (!selectedEndpointName) return;

    try {
      await generateScripts(selectedEndpointName).unwrap();
      setGenerateDialogOpen(false);
      setSelectedEndpointName("");
      refetch();
    } catch (err) {
      console.error("Failed to generate scripts:", err);
    }
  };

  const handleExportScripts = async () => {
    if (!selectedEndpointName) return;

    try {
      const result = await exportScripts(selectedEndpointName).unwrap();

      // Download the file
      const blob = new Blob([result.file_content], { type: "text/x-python" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedEndpointName}_validation.py`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setExportDialogOpen(false);
      setSelectedEndpointName("");
    } catch (err) {
      console.error("Failed to export scripts:", err);
    }
  };

  const handleAccordionChange =
    (scriptId: string) => (_: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedScript(isExpanded ? scriptId : false);
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
              Validation Scripts
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View and manage validation scripts for your endpoints
            </Typography>
          </Box>
          <Box sx={{ display: "flex", gap: 2 }}>
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={() => setExportDialogOpen(true)}
            >
              Export to Python
            </Button>
            <Button
              variant="contained"
              startIcon={<Code />}
              onClick={() => setGenerateDialogOpen(true)}
            >
              Generate Scripts
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
              placeholder="Search scripts..."
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

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <FilterList fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {filteredScripts.length} of {scripts.length} scripts
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Scripts List */}
      {filteredScripts.length === 0 ? (
        <Card>
          <CardContent>
            <Box sx={{ textAlign: "center", py: 6 }}>
              <Code sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No validation scripts found
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                {scripts.length === 0
                  ? "Generate validation scripts from your endpoints to get started"
                  : "Try adjusting your filters"}
              </Typography>
              {scripts.length === 0 && (
                <Button
                  variant="outlined"
                  startIcon={<Code />}
                  onClick={() => setGenerateDialogOpen(true)}
                >
                  Generate Scripts
                </Button>
              )}
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {filteredScripts.map((script) => (
            <Accordion
              key={script.id}
              expanded={expandedScript === script.id}
              onChange={handleAccordionChange(script.id)}
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
                  <Code color="primary" />
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {script.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {script.description}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Endpoint:{" "}
                      {script.endpoint_id
                        ? script.endpoint_id.slice(0, 8) + "..."
                        : "N/A"}
                    </Typography>
                  </Box>
                  <Chip
                    label={script.script_type.replace(/_/g, " ").toUpperCase()}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                  {script.constraint_id && (
                    <Chip
                      label={`Constraint: ${script.constraint_id.slice(
                        0,
                        8
                      )}...`}
                      size="small"
                      color="secondary"
                      variant="outlined"
                    />
                  )}
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
                        label={script.script_type
                          .replace(/_/g, " ")
                          .toUpperCase()}
                        color="primary"
                        variant="outlined"
                      />
                    </Grid>
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Related Constraint
                      </Typography>
                      {script.constraint_id ? (
                        <Chip
                          label={`${script.constraint_id.slice(0, 8)}...`}
                          color="secondary"
                          variant="outlined"
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No constraint mapping
                        </Typography>
                      )}
                    </Grid>
                    <Grid size={{ xs: 12 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Description
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {script.description}
                      </Typography>
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
                    />
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
          count={scriptsData?.pagination.total_items || 0}
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

      {/* Generate Scripts Dialog */}
      <Dialog
        open={generateDialogOpen}
        onClose={() => setGenerateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Generate Validation Scripts</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select an endpoint to automatically generate validation scripts
              based on its constraints.
            </Typography>

            {generateError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                Failed to generate scripts. Please try again.
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
          <Button onClick={() => setGenerateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleGenerateScripts}
            variant="contained"
            disabled={!selectedEndpointName || isGenerating}
          >
            {isGenerating ? "Generating..." : "Generate Scripts"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Export Scripts Dialog */}
      <Dialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Export Validation Scripts</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Select an endpoint to export its validation scripts as a Python
              file.
            </Typography>

            {exportError && (
              <Alert severity="error" sx={{ mb: 3 }}>
                Failed to export scripts. Please try again.
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
          <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleExportScripts}
            variant="contained"
            disabled={!selectedEndpointName || isExporting}
            startIcon={<Download />}
          >
            {isExporting ? "Exporting..." : "Export"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ValidationScriptsPage;
