import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { BarChart, PieChart, TrendingUp } from "@mui/icons-material";
import type { SequenceStatistics } from "@/types";

interface StatisticsDashboardProps {
  statistics?: SequenceStatistics;
  isLoading?: boolean;
}

export default function StatisticsDashboard({
  statistics,
  isLoading,
}: StatisticsDashboardProps) {
  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>
          Loading statistics...
        </Typography>
      </Box>
    );
  }

  if (!statistics) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="h6" color="text.secondary">
          No statistics available
        </Typography>
      </Box>
    );
  }

  const sequencesByTypeEntries = Object.entries(statistics.sequences_by_type);
  const sequencesByPriorityEntries = Object.entries(
    statistics.sequences_by_priority
  );

  return (
    <Box sx={{ p: 3 }}>
      <Grid container spacing={3}>
        {/* Overview Cards */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <BarChart color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Total Sequences</Typography>
              </Box>
              <Typography variant="h4" color="primary" fontWeight="bold">
                {statistics.total_sequences}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Generated sequences
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <PieChart color="secondary" sx={{ mr: 1 }} />
                <Typography variant="h6">With Dependencies</Typography>
              </Box>
              <Typography variant="h4" color="secondary" fontWeight="bold">
                {statistics.sequences_with_dependencies}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {statistics.total_sequences > 0
                  ? `${Math.round(
                      (statistics.sequences_with_dependencies /
                        statistics.total_sequences) *
                        100
                    )}% of total`
                  : "0% of total"}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <TrendingUp color="success" sx={{ mr: 1 }} />
                <Typography variant="h6">Avg Operations</Typography>
              </Box>
              <Typography variant="h4" color="success.main" fontWeight="bold">
                {statistics.average_operations_per_sequence.toFixed(1)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Operations per sequence
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <BarChart color="warning" sx={{ mr: 1 }} />
                <Typography variant="h6">Sequence Types</Typography>
              </Box>
              <Typography variant="h4" color="warning.main" fontWeight="bold">
                {sequencesByTypeEntries.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Different types
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Sequences by Type */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sequences by Type
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {sequencesByTypeEntries.map(([type, count]) => (
                  <Box
                    key={type}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Chip
                        label={type}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 2,
                        minWidth: 120,
                      }}
                    >
                      <Box sx={{ width: 100 }}>
                        <LinearProgress
                          variant="determinate"
                          value={(count / statistics.total_sequences) * 100}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                      <Typography
                        variant="body2"
                        fontWeight="medium"
                        sx={{ minWidth: 20 }}
                      >
                        {count}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Sequences by Priority */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sequences by Priority
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {sequencesByPriorityEntries.map(([priority, count]) => {
                  const priorityNum = parseInt(priority);
                  const priorityLabel =
                    priorityNum === 1
                      ? "High"
                      : priorityNum === 2
                      ? "Medium"
                      : "Low";
                  const priorityColor =
                    priorityNum === 1
                      ? "error"
                      : priorityNum === 2
                      ? "warning"
                      : "success";

                  return (
                    <Box
                      key={priority}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                      }}
                    >
                      <Box
                        sx={{ display: "flex", alignItems: "center", gap: 1 }}
                      >
                        <Chip
                          label={priorityLabel}
                          size="small"
                          color={
                            priorityColor as "error" | "warning" | "success"
                          }
                          variant="outlined"
                        />
                        <Typography variant="caption" color="text.secondary">
                          (Priority {priority})
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 2,
                          minWidth: 120,
                        }}
                      >
                        <Box sx={{ width: 100 }}>
                          <LinearProgress
                            variant="determinate"
                            value={(count / statistics.total_sequences) * 100}
                            sx={{ height: 6, borderRadius: 3 }}
                          />
                        </Box>
                        <Typography
                          variant="body2"
                          fontWeight="medium"
                          sx={{ minWidth: 20 }}
                        >
                          {count}
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Summary Stats */}
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Summary
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography variant="h5" color="primary" fontWeight="bold">
                      {statistics.total_sequences}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Sequences
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="h5"
                      color="secondary"
                      fontWeight="bold"
                    >
                      {statistics.sequences_with_dependencies}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Have Dependencies
                    </Typography>
                  </Box>
                </Grid>
                <Grid size={{ xs: 12, sm: 4 }}>
                  <Box sx={{ textAlign: "center", p: 2 }}>
                    <Typography
                      variant="h5"
                      color="success.main"
                      fontWeight="bold"
                    >
                      {statistics.average_operations_per_sequence.toFixed(1)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg Operations
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
