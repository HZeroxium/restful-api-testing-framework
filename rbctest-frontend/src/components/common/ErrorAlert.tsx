import React from "react";
import { Alert, type AlertProps, Button, Box } from "@mui/material";
import { Refresh } from "@mui/icons-material";

interface ErrorAlertProps extends Omit<AlertProps, "action"> {
  error?: string;
  onRetry?: () => void;
  retryLabel?: string;
  showRetry?: boolean;
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({
  error,
  onRetry,
  retryLabel = "Retry",
  showRetry = true,
  severity = "error",
  ...props
}) => {
  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    }
  };

  return (
    <Alert
      severity={severity}
      action={
        showRetry &&
        onRetry && (
          <Button
            color="inherit"
            size="small"
            onClick={handleRetry}
            startIcon={<Refresh />}
            sx={{ fontWeight: 500 }}
          >
            {retryLabel}
          </Button>
        )
      }
      sx={{
        borderRadius: 2,
        "& .MuiAlert-message": {
          width: "100%",
        },
        "& .MuiAlert-action": {
          alignItems: "flex-start",
          paddingTop: 0.5,
        },
      }}
      {...props}
    >
      <Box>
        <Box sx={{ fontWeight: 500, mb: 0.5 }}>
          {props.title || "Something went wrong"}
        </Box>
        {error && (
          <Box sx={{ fontSize: "0.875rem", opacity: 0.9 }}>{error}</Box>
        )}
        {props.children}
      </Box>
    </Alert>
  );
};

export default ErrorAlert;
export { ErrorAlert };
