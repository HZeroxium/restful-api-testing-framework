import {
  Dialog,
  DialogTitle,
  DialogContent,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Box,
  Chip,
  IconButton,
} from "@mui/material";
import { Close, CheckCircle, Error } from "@mui/icons-material";
import type { BatchResult } from "@/types";

interface BatchProgressDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  results: BatchResult[];
  isLoading: boolean;
}

export default function BatchProgressDialog({
  open,
  onClose,
  title,
  results,
  isLoading,
}: BatchProgressDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {title}
        <IconButton
          onClick={onClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {isLoading && <LinearProgress sx={{ mb: 2 }} />}
        <List>
          {results.map((result, index) => (
            <ListItem key={index}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  width: "100%",
                }}
              >
                {result.success ? (
                  <CheckCircle color="success" />
                ) : (
                  <Error color="error" />
                )}
                <ListItemText
                  primary={result.endpoint_name}
                  secondary={
                    result.error_message ||
                    `${result.execution_time_ms.toFixed(0)}ms`
                  }
                />
                <Chip
                  label={result.success ? "Success" : "Failed"}
                  color={result.success ? "success" : "error"}
                  size="small"
                />
              </Box>
            </ListItem>
          ))}
        </List>
      </DialogContent>
    </Dialog>
  );
}
