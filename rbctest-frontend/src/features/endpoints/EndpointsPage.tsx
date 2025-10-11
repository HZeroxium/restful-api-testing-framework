import React, { useState } from "react";
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
} from "@mui/material";
import { Search, FilterList, Api } from "@mui/icons-material";
import { useGetEndpointsQuery } from "@/services/api";
import { LoadingOverlay } from "@/components/common/LoadingOverlay";
import { ErrorAlert } from "@/components/common/ErrorAlert";
import { DataTable } from "@/components/common/DataTable";
import type { EndpointResponse, TableColumn } from "@/types";

const EndpointsPage: React.FC = () => {
  const navigate = useNavigate();
  const [page] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [methodFilter, setMethodFilter] = useState<string>("all");

  const { data, isLoading, error, refetch } = useGetEndpointsQuery({
    page,
    size: 50,
  });

  const endpoints = data?.endpoints || [];

  // Filter endpoints based on search and method
  const filteredEndpoints = endpoints.filter((endpoint) => {
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
  });

  const handleEndpointClick = (endpoint: EndpointResponse) => {
    navigate(`/endpoints/${endpoint.id}`);
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
            />
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default EndpointsPage;
