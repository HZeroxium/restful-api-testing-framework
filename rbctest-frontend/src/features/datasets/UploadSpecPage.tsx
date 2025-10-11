import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Alert,
  LinearProgress,
  Chip,
  Divider,
} from "@mui/material";
import {
  CheckCircle,
  Api,
  FolderOpen,
  Link as LinkIcon,
} from "@mui/icons-material";
import { useUploadSpecMutation } from "@/services/api";
import { FileUploadZone } from "@/components/common/FileUploadZone";
import type { CreateDatasetFromFileResponse } from "@/types";

const UploadSpecPage: React.FC = () => {
  const navigate = useNavigate();
  const [uploadSpec, { isLoading }] = useUploadSpecMutation();

  const [uploadResult, setUploadResult] =
    useState<CreateDatasetFromFileResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = async (files: File[]) => {
    const file = files[0];
    if (!file) return;

    // Validate file type
    const validTypes = [".json", ".yaml", ".yml"];
    const fileExtension = file.name
      .substring(file.name.lastIndexOf("."))
      .toLowerCase();

    if (!validTypes.some((type) => type === fileExtension)) {
      setError(
        "Please upload a valid OpenAPI specification file (.json, .yaml, or .yml)"
      );
      return;
    }

    // Create FormData
    const formData = new FormData();
    formData.append("file", file);

    try {
      setError(null);
      const result = await uploadSpec(formData).unwrap();
      setUploadResult(result);
    } catch (err: any) {
      console.error("Upload failed:", err);
      setError(err?.data?.detail || "Failed to upload specification file");
      setUploadResult(null);
    }
  };

  const handleReset = () => {
    setUploadResult(null);
    setError(null);
  };

  const handleViewDataset = () => {
    if (uploadResult) {
      navigate(`/datasets/${uploadResult.dataset_id}`);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600, mb: 1 }}>
          Upload OpenAPI Specification
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload an OpenAPI specification file to automatically create a dataset
          and extract endpoints
        </Typography>
      </Box>

      {/* Upload Section */}
      {!uploadResult && (
        <Card>
          <CardContent>
            <FileUploadZone
              onFilesSelected={handleFileSelect}
              acceptedTypes={[
                "application/json",
                "application/x-yaml",
                "text/yaml",
              ]}
              maxFiles={1}
              disabled={isLoading}
            />

            {isLoading && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Processing specification file...
                </Typography>
                <LinearProgress />
              </Box>
            )}

            {error && (
              <Alert
                severity="error"
                sx={{ mt: 3 }}
                onClose={() => setError(null)}
              >
                {error}
              </Alert>
            )}

            <Box sx={{ mt: 3 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: 600 }}
              >
                Supported Formats:
              </Typography>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                <Chip label="JSON (.json)" size="small" variant="outlined" />
                <Chip label="YAML (.yaml)" size="small" variant="outlined" />
                <Chip label="YML (.yml)" size="small" variant="outlined" />
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Success Result */}
      {uploadResult && (
        <Card>
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 3 }}>
              <CheckCircle sx={{ fontSize: 48, color: "success.main" }} />
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 600 }}>
                  Upload Successful!
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Your OpenAPI specification has been processed
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Dataset Information */}
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: 600 }}
              >
                Dataset Information
              </Typography>
              <Box
                sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 2 }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <FolderOpen sx={{ fontSize: 20, color: "text.secondary" }} />
                  <Typography variant="body2">
                    <strong>Dataset Name:</strong> {uploadResult.dataset_name}
                  </Typography>
                </Box>

                {uploadResult.api_title && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Api sx={{ fontSize: 20, color: "text.secondary" }} />
                    <Typography variant="body2">
                      <strong>API Title:</strong> {uploadResult.api_title}
                    </Typography>
                  </Box>
                )}

                {uploadResult.spec_version && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Api sx={{ fontSize: 20, color: "text.secondary" }} />
                    <Typography variant="body2">
                      <strong>OpenAPI Version:</strong>{" "}
                      {uploadResult.spec_version}
                    </Typography>
                  </Box>
                )}

                {uploadResult.base_url && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <LinkIcon sx={{ fontSize: 20, color: "text.secondary" }} />
                    <Typography variant="body2">
                      <strong>Base URL:</strong> {uploadResult.base_url}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Box>

            <Divider sx={{ my: 3 }} />

            {/* Endpoints Summary */}
            <Box sx={{ mb: 3 }}>
              <Typography
                variant="subtitle2"
                gutterBottom
                sx={{ fontWeight: 600 }}
              >
                Endpoints Summary
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Alert severity="success" icon={<CheckCircle />}>
                  Successfully extracted{" "}
                  <strong>{uploadResult.endpoints_count}</strong> endpoint
                  {uploadResult.endpoints_count !== 1 ? "s" : ""} from the
                  specification
                </Alert>
              </Box>
            </Box>

            {/* Actions */}
            <Box
              sx={{
                display: "flex",
                gap: 2,
                justifyContent: "flex-end",
                mt: 4,
              }}
            >
              <Button variant="outlined" onClick={handleReset}>
                Upload Another
              </Button>
              <Button variant="contained" onClick={handleViewDataset}>
                View Dataset
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      {!uploadResult && !isLoading && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography
              variant="subtitle2"
              gutterBottom
              sx={{ fontWeight: 600 }}
            >
              What happens when you upload a specification?
            </Typography>
            <Box component="ol" sx={{ pl: 2, mt: 2 }}>
              <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                A new dataset is created with the API information
              </Typography>
              <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                All endpoints are automatically extracted and stored
              </Typography>
              <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                Request/response schemas are parsed and saved
              </Typography>
              <Typography component="li" variant="body2" sx={{ mb: 1 }}>
                Authentication requirements are identified
              </Typography>
              <Typography component="li" variant="body2">
                You can then generate constraints, validation scripts, and test
                data for each endpoint
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default UploadSpecPage;
