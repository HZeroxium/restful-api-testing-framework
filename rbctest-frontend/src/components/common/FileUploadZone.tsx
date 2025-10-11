import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  Box,
  Typography,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from "@mui/material";
import { CloudUpload, Description, Delete } from "@mui/icons-material";

interface FileUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes?: string[];
  maxFiles?: number;
  maxSize?: number; // in bytes
  disabled?: boolean;
  existingFiles?: File[];
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onFilesSelected,
  acceptedTypes = ["application/json", "text/yaml", "text/yml"],
  maxFiles = 1,
  maxSize = 10 * 1024 * 1024, // 10MB
  disabled = false,
  existingFiles = [],
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setError(null);

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === "file-too-large") {
          setError(
            `File is too large. Maximum size is ${Math.round(
              maxSize / 1024 / 1024
            )}MB.`
          );
        } else if (rejection.errors[0]?.code === "file-invalid-type") {
          setError(
            `Invalid file type. Accepted types: ${acceptedTypes.join(", ")}`
          );
        } else {
          setError("File was rejected. Please check the file type and size.");
        }
        return;
      }

      // Handle accepted files
      if (acceptedFiles.length > 0) {
        setUploading(true);
        setUploadProgress(0);

        // Simulate upload progress
        const interval = setInterval(() => {
          setUploadProgress((prev) => {
            if (prev >= 100) {
              clearInterval(interval);
              setUploading(false);
              onFilesSelected(acceptedFiles);
              return 100;
            }
            return prev + 10;
          });
        }, 100);
      }
    },
    [acceptedTypes, maxSize, onFilesSelected]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes.reduce((acc, type) => {
      acc[type] = [];
      return acc;
    }, {} as Record<string, string[]>),
    maxFiles,
    maxSize,
    disabled: disabled || uploading,
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const removeFile = (_index: number) => {
    // Note: This would need to be handled by parent component
    // const newFiles = existingFiles.filter((_, i) => i !== index);
    // onFilesSelected(newFiles);
  };

  return (
    <Box sx={{ width: "100%" }}>
      {/* Upload Zone */}
      <Box
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: "center",
          cursor: disabled || uploading ? "not-allowed" : "pointer",
          border: "2px dashed",
          borderColor: isDragActive ? "primary.main" : "grey.300",
          backgroundColor: isDragActive ? "primary.50" : "background.paper",
          transition: "all 0.2s ease-in-out",
          opacity: disabled || uploading ? 0.6 : 1,
          "&:hover": {
            borderColor: disabled || uploading ? "grey.300" : "primary.main",
            backgroundColor:
              disabled || uploading ? "background.paper" : "primary.50",
          },
        }}
      >
        <input {...getInputProps()} />

        <CloudUpload
          sx={{
            fontSize: 48,
            color: isDragActive ? "primary.main" : "grey.400",
            mb: 2,
          }}
        />

        {uploading ? (
          <Box>
            <Typography variant="h6" gutterBottom>
              Uploading...
            </Typography>
            <LinearProgress
              variant="determinate"
              value={uploadProgress}
              sx={{ mb: 2 }}
            />
            <Typography variant="body2" color="text.secondary">
              {uploadProgress}% complete
            </Typography>
          </Box>
        ) : (
          <Box>
            <Typography variant="h6" gutterBottom>
              {isDragActive ? "Drop files here" : "Drag & drop files here"}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              or click to select files
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Accepted formats: {acceptedTypes.join(", ")} • Max {maxFiles} file
              {maxFiles > 1 ? "s" : ""} • Max{" "}
              {Math.round(maxSize / 1024 / 1024)}MB
            </Typography>
          </Box>
        )}
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {/* File List */}
      {existingFiles.length > 0 && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Selected Files:
          </Typography>
          <List dense>
            {existingFiles.map((file, index) => (
              <ListItem
                key={`${file.name}-${index}`}
                sx={{
                  backgroundColor: "grey.50",
                  borderRadius: 1,
                  mb: 0.5,
                }}
              >
                <Description sx={{ mr: 1, color: "text.secondary" }} />
                <ListItemText
                  primary={file.name}
                  secondary={formatFileSize(file.size)}
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => removeFile(index)}
                    size="small"
                  >
                    <Delete />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      )}
    </Box>
  );
};

export default FileUploadZone;
export { FileUploadZone };
