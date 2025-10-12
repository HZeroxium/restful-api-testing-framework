import { Chip, Tooltip, CircularProgress } from "@mui/material";
import { FiberManualRecord } from "@mui/icons-material";
import { useGetHealthStatusQuery } from "@/services/api";

export default function HealthIndicator() {
  const { data, isLoading, error } = useGetHealthStatusQuery(undefined, {
    pollingInterval: 30000, // Poll every 30 seconds
  });

  if (isLoading) {
    return <CircularProgress size={20} />;
  }

  const isHealthy = data?.status === "healthy" && !error;

  return (
    <Tooltip title={isHealthy ? "System Healthy" : "System Unhealthy"}>
      <Chip
        icon={<FiberManualRecord />}
        label={isHealthy ? "Online" : "Offline"}
        size="small"
        color={isHealthy ? "success" : "error"}
        variant="outlined"
      />
    </Tooltip>
  );
}
