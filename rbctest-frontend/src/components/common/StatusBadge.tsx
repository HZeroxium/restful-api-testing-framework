import React from "react";
import { Chip, type ChipProps } from "@mui/material";
import { CheckCircle, Error, Schedule, Cancel } from "@mui/icons-material";

interface StatusBadgeProps extends Omit<ChipProps, "label"> {
  status: string;
  variant?: "filled" | "outlined";
  size?: "small" | "medium";
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant = "filled",
  size = "small",
  ...props
}) => {
  const getStatusConfig = (status: string) => {
    const normalizedStatus = status.toLowerCase();

    switch (normalizedStatus) {
      case "success":
      case "completed":
      case "passed":
      case "valid":
        return {
          label: "Success",
          color: "success" as const,
          icon: <CheckCircle fontSize="small" />,
        };

      case "error":
      case "failed":
      case "invalid":
      case "cancelled":
        return {
          label: "Failed",
          color: "error" as const,
          icon: <Error fontSize="small" />,
        };

      case "warning":
      case "pending":
        return {
          label: "Pending",
          color: "warning" as const,
          icon: <Schedule fontSize="small" />,
        };

      case "running":
      case "processing":
        return {
          label: "Running",
          color: "info" as const,
          icon: <Schedule fontSize="small" />,
        };

      case "cancelled":
        return {
          label: "Cancelled",
          color: "default" as const,
          icon: <Cancel fontSize="small" />,
        };

      default:
        return {
          label: status,
          color: "default" as const,
          icon: <Schedule fontSize="small" />,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <Chip
      label={config.label}
      color={config.color}
      variant={variant}
      size={size}
      icon={config.icon}
      sx={{
        fontWeight: 500,
        "& .MuiChip-icon": {
          fontSize: "1rem",
        },
      }}
      {...props}
    />
  );
};

export default StatusBadge;
export { StatusBadge };
export { default as FullPipelineDialog } from "./FullPipelineDialog";
