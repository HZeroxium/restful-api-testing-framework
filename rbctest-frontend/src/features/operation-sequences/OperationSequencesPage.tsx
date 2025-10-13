import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Switch,
  FormControlLabel,
  IconButton,
  Menu,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  Search,
  PlayArrow,
  MoreVert,
  ViewList,
  AccountTree as GraphIcon,
  BarChart,
  Delete,
  Edit,
  Visibility,
} from "@mui/icons-material";
import {
  useGetSequenceStatisticsQuery,
  useGenerateSequencesMutation,
  useDeleteSequenceMutation,
  useGetSequencesByDatasetQuery,
  useGetDependencyGraphQuery,
} from "@/services/api";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import ReactFlowGraph from "@/components/graphs/ReactFlowGraph";
import ThreeJsGraph from "@/components/graphs/ThreeJsGraph";
import { usePagination } from "@/hooks/usePagination";
import type { OperationSequenceResponse, TableColumn } from "@/types";
import { sequencesToDependencyGraph } from "@/utils/operationSequence.mappers";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";

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
      id={`sequences-tabpanel-${index}`}
      aria-labelledby={`sequences-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const OperationSequencesPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const datasetId = searchParams.get("dataset") || "";

  const [activeTab, setActiveTab] = useState(0);
  const [graphType, setGraphType] = useState<"2d" | "3d">("2d");

  const {
    page,
    pageSize,
    handlePageChange,
    handlePageSizeChange,
    resetPagination,
  } = usePagination({ defaultPageSize: 20 });

  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");

  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [overrideExisting, setOverrideExisting] = useState(true);

  const [selectedSequence, setSelectedSequence] =
    useState<OperationSequenceResponse | null>(null);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Reset pagination when filters change
  useEffect(() => {
    resetPagination();
  }, [searchTerm, typeFilter, priorityFilter, resetPagination]);

  // Backend data for graph/sequences if dataset is provided
  const { data: statistics } = useGetSequenceStatisticsQuery();
  const [generateSequences, { isLoading: isGenerating }] =
    useGenerateSequencesMutation();
  const [deleteSequence] = useDeleteSequenceMutation();

  const {
    data: backendGraph,
    isLoading: isLoadingGraph,
    error: graphError,
  } = useGetDependencyGraphQuery(datasetId!, { skip: !datasetId });

  const { data: sequencesList, isLoading: isLoadingSeq } =
    useGetSequencesByDatasetQuery(
      { datasetId, limit: 50, offset: 0 },
      { skip: !datasetId }
    );

  // Graph data selection: prefer backendGraph, else derive from sequences
  const derivedGraph = backendGraph ||
    (sequencesList &&
      sequencesToDependencyGraph(sequencesList.sequences || [])) || {
      nodes: [],
      edges: [],
      metadata: {},
    };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleGenerateSequences = async () => {
    if (!datasetId) return;

    try {
      await generateSequences({
        datasetId,
        body: { override_existing: overrideExisting },
      }).unwrap();
      setGenerateDialogOpen(false);
    } catch (err) {
      console.error("Failed to generate sequences:", err);
    }
  };

  const handleMenuOpen = (
    event: React.MouseEvent<HTMLElement>,
    sequence: OperationSequenceResponse
  ) => {
    setMenuAnchor(event.currentTarget);
    setSelectedSequence(sequence);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedSequence(null);
  };

  const handleDeleteSequence = async () => {
    if (!selectedSequence) return;

    try {
      await deleteSequence(selectedSequence.id).unwrap();
      setDeleteDialogOpen(false);
      setSelectedSequence(null);
    } catch (err) {
      console.error("Failed to delete sequence:", err);
    }
  };

  const columns: TableColumn<OperationSequenceResponse>[] = [
    {
      key: "name",
      label: "Name",
      render: (name) => (
        <Typography variant="body2" fontWeight="medium">
          {name}
        </Typography>
      ),
    },
    {
      key: "description",
      label: "Description",
    },
    {
      key: "sequence_type",
      label: "Type",
      render: (type) => <Chip label={type} size="small" color="primary" />,
    },
    {
      key: "priority",
      label: "Priority",
    },
    {
      key: "operations",
      label: "Operations",
      render: (operations) => (
        <Typography variant="body2">{operations.length} operations</Typography>
      ),
    },
    {
      key: "estimated_duration",
      label: "Duration",
      render: (duration) => (
        <Typography variant="body2">
          {duration ? `${duration.toFixed(1)}s` : "N/A"}
        </Typography>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (_, row) => (
        <IconButton
          aria-label="more"
          onClick={(event) => handleMenuOpen(event, row)}
        >
          <MoreVert />
        </IconButton>
      ),
    },
  ];

  // Filter sequences
  const listSequences: OperationSequenceResponse[] =
    sequencesList?.sequences || [];

  const filteredSequences = listSequences.filter((sequence) => {
    const matchesSearch =
      searchTerm === "" ||
      sequence.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sequence.description.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesType =
      typeFilter === "all" || sequence.sequence_type === typeFilter;
    const matchesPriority =
      priorityFilter === "all" ||
      sequence.priority.toString() === priorityFilter;

    return matchesSearch && matchesType && matchesPriority;
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h4">Operation Sequences</Typography>
        <Button
          variant="contained"
          startIcon={<PlayArrow />}
          onClick={() => setGenerateDialogOpen(true)}
          disabled={!datasetId}
        >
          Generate Sequences
        </Button>
      </Box>

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="sequences tabs"
          >
            <Tab icon={<ViewList />} label="List View" iconPosition="start" />
            <Tab icon={<GraphIcon />} label="Graph View" iconPosition="start" />
            <Tab icon={<BarChart />} label="Statistics" iconPosition="start" />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          <Box sx={{ mb: 2 }}>
            <Box
              sx={{
                display: "flex",
                gap: 2,
                mb: 2,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <TextField
                label="Search Sequences"
                variant="outlined"
                size="small"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
                sx={{ flexGrow: 1, maxWidth: 300 }}
              />
              <FormControl sx={{ minWidth: 120 }} size="small">
                <InputLabel>Type</InputLabel>
                <Select
                  value={typeFilter}
                  label="Type"
                  onChange={(e) => setTypeFilter(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="workflow">Workflow</MenuItem>
                  <MenuItem value="crud">CRUD</MenuItem>
                  <MenuItem value="data_flow">Data Flow</MenuItem>
                </Select>
              </FormControl>
              <FormControl sx={{ minWidth: 120 }} size="small">
                <InputLabel>Priority</InputLabel>
                <Select
                  value={priorityFilter}
                  label="Priority"
                  onChange={(e) => setPriorityFilter(e.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="1">High</MenuItem>
                  <MenuItem value="2">Medium</MenuItem>
                  <MenuItem value="3">Low</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell key={column.key}>{column.label}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredSequences.map((sequence) => (
                    <TableRow key={sequence.id}>
                      {columns.map((column) => (
                        <TableCell key={column.key}>
                          {column.render
                            ? column.render(
                                sequence[
                                  column.key as keyof OperationSequenceResponse
                                ],
                                sequence
                              )
                            : (() => {
                                const value =
                                  sequence[
                                    column.key as keyof OperationSequenceResponse
                                  ];
                                if (
                                  typeof value === "object" &&
                                  value !== null
                                ) {
                                  return JSON.stringify(value);
                                }
                                return value;
                              })()}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              component="div"
              count={filteredSequences.length}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={pageSize}
              onRowsPerPageChange={handlePageSizeChange}
              rowsPerPageOptions={[10, 20, 50]}
            />
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box
            sx={{
              mb: 2,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
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
            </Box>
          </Box>

          {(isLoadingGraph || isLoadingSeq) && <LoadingOverlay open={true} />}
          {graphError && <ErrorAlert error={graphError.toString()} />}
          {!isLoadingGraph &&
            !isLoadingSeq &&
            (graphType === "2d" ? (
              <ReactFlowGraph
                graphData={derivedGraph}
                onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
                onEdgeClick={(edgeId) => console.log("Edge clicked:", edgeId)}
                autoLayout="grid"
              />
            ) : (
              <ThreeJsGraph
                graphData={derivedGraph}
                onNodeClick={(nodeId) => console.log("Node clicked:", nodeId)}
              />
            ))}
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="primary">
                    {statistics?.total_sequences || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Sequences
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="secondary">
                    {statistics?.sequences_with_dependencies || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    With Dependencies
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="success.main">
                    {statistics?.average_operations_per_sequence?.toFixed(1) ||
                      "0.0"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg Operations
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography variant="h4" color="warning.main">
                    {listSequences.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Sequences
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Generate Sequences Dialog */}
      <Dialog
        open={generateDialogOpen}
        onClose={() => setGenerateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Generate Operation Sequences</DialogTitle>
        <DialogContent>
          <FormControlLabel
            control={
              <Switch
                checked={overrideExisting}
                onChange={(e) => setOverrideExisting(e.target.checked)}
                color="primary"
              />
            }
            label="Override existing sequences"
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This will analyze the dataset endpoints and generate operation
            sequences based on their dependencies.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGenerateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleGenerateSequences}
            variant="contained"
            disabled={isGenerating}
          >
            {isGenerating ? "Generating..." : "Generate"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem
          onClick={() => {
            navigate(`/operation-sequences/${selectedSequence?.id}`);
            handleMenuClose();
          }}
        >
          <ListItemIcon>
            <Visibility fontSize="small" />
          </ListItemIcon>
          <ListItemText>View Details</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <Edit fontSize="small" />
          </ListItemIcon>
          <ListItemText>Edit</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            setDeleteDialogOpen(true);
            handleMenuClose();
          }}
        >
          <ListItemIcon>
            <Delete fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onCancel={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteSequence}
        title="Delete Sequence"
        message={`Are you sure you want to delete "${selectedSequence?.name}"? This action cannot be undone.`}
        severity="warning"
      />
    </Box>
  );
};

export default OperationSequencesPage;
