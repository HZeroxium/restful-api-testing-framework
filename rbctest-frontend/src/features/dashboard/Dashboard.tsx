import React from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress,
} from "@mui/material";
import {
  FolderOpen,
  List as ListIcon,
  PlayArrow,
  CheckCircle,
  Upload,
  Schedule,
} from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import StatusBadge from "@/components/common/StatusBadge";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  // Mock data - in real app, this would come from API
  const metrics = {
    totalDatasets: 12,
    totalEndpoints: 45,
    recentExecutions: 8,
    successRate: 87.5,
  };

  const recentActivity = [
    {
      id: 1,
      name: "Pet Store API",
      type: "dataset",
      action: "uploaded",
      time: "2 hours ago",
    },
    {
      id: 2,
      name: "User Management API",
      type: "dataset",
      action: "uploaded",
      time: "4 hours ago",
    },
    {
      id: 3,
      name: "Payment API",
      type: "dataset",
      action: "uploaded",
      time: "1 day ago",
    },
    {
      id: 4,
      name: "Inventory API",
      type: "dataset",
      action: "uploaded",
      time: "2 days ago",
    },
    {
      id: 5,
      name: "Notification API",
      type: "dataset",
      action: "uploaded",
      time: "3 days ago",
    },
  ];

  const recentExecutions = [
    {
      id: 1,
      endpoint: "GET /users",
      status: "completed",
      tests: 15,
      passed: 14,
      time: "1 hour ago",
    },
    {
      id: 2,
      endpoint: "POST /orders",
      status: "completed",
      tests: 12,
      passed: 12,
      time: "2 hours ago",
    },
    {
      id: 3,
      endpoint: "PUT /products",
      status: "failed",
      tests: 8,
      passed: 6,
      time: "3 hours ago",
    },
    {
      id: 4,
      endpoint: "DELETE /items",
      status: "completed",
      tests: 10,
      passed: 10,
      time: "4 hours ago",
    },
    {
      id: 5,
      endpoint: "GET /analytics",
      status: "running",
      tests: 20,
      passed: 0,
      time: "5 minutes ago",
    },
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle color="success" fontSize="small" />;
      case "failed":
        return <CheckCircle color="error" fontSize="small" />;
      case "running":
        return <Schedule color="info" fontSize="small" />;
      default:
        return <Schedule fontSize="small" />;
    }
  };

  const getSuccessRate = (passed: number, total: number) => {
    return total > 0 ? (passed / total) * 100 : 0;
  };

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          sx={{ fontWeight: 600 }}
        >
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Overview of your API testing framework
        </Typography>
      </Box>

      {/* Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <FolderOpen color="primary" sx={{ mr: 1 }} />
                <Typography
                  variant="h6"
                  component="div"
                  sx={{ fontWeight: 600 }}
                >
                  {metrics.totalDatasets}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Total Datasets
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <ListIcon color="primary" sx={{ mr: 1 }} />
                <Typography
                  variant="h6"
                  component="div"
                  sx={{ fontWeight: 600 }}
                >
                  {metrics.totalEndpoints}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Total Endpoints
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <PlayArrow color="primary" sx={{ mr: 1 }} />
                <Typography
                  variant="h6"
                  component="div"
                  sx={{ fontWeight: 600 }}
                >
                  {metrics.recentExecutions}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Recent Executions (24h)
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <Typography
                  variant="h6"
                  component="div"
                  sx={{ fontWeight: 600 }}
                >
                  {metrics.successRate}%
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Success Rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Quick Actions
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Button
                variant="contained"
                startIcon={<Upload />}
                fullWidth
                onClick={() => navigate("/datasets/upload")}
                sx={{ py: 1.5 }}
              >
                Upload OpenAPI Spec
              </Button>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Button
                variant="outlined"
                startIcon={<PlayArrow />}
                fullWidth
                onClick={() => navigate("/executions")}
                sx={{ py: 1.5 }}
              >
                Run Full Pipeline
              </Button>
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Button
                variant="outlined"
                startIcon={<FolderOpen />}
                fullWidth
                onClick={() => navigate("/datasets")}
                sx={{ py: 1.5 }}
              >
                View All Datasets
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        {/* Recent Activity */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Recent Activity
              </Typography>
              <List dense>
                {recentActivity.map((activity, index) => (
                  <React.Fragment key={activity.id}>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 40 }}>
                        <FolderOpen fontSize="small" color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${activity.name} ${activity.action}`}
                        secondary={activity.time}
                        primaryTypographyProps={{ fontSize: "0.875rem" }}
                        secondaryTypographyProps={{ fontSize: "0.75rem" }}
                      />
                    </ListItem>
                    {index < recentActivity.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Executions */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Recent Executions
              </Typography>
              <List dense>
                {recentExecutions.map((execution, index) => (
                  <React.Fragment key={execution.id}>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 40 }}>
                        {getStatusIcon(execution.status)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Typography
                              variant="body2"
                              sx={{ fontWeight: 500 }}
                            >
                              {execution.endpoint}
                            </Typography>
                            <StatusBadge
                              status={execution.status}
                              size="small"
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography
                              variant="caption"
                              color="text.secondary"
                            >
                              {execution.passed}/{execution.tests} tests passed
                              • {execution.time}
                            </Typography>
                            <LinearProgress
                              variant="determinate"
                              value={getSuccessRate(
                                execution.passed,
                                execution.tests
                              )}
                              sx={{ mt: 0.5, height: 4, borderRadius: 2 }}
                            />
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < recentExecutions.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
