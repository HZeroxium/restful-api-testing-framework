import { Component, type ErrorInfo, type ReactNode } from "react";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Container,
} from "@mui/material";
import { Refresh, ErrorOutline, BugReport } from "@mui/icons-material";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | undefined;
  errorInfo: ErrorInfo | undefined;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: undefined, errorInfo: undefined };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error, errorInfo: undefined };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to console in development
    if (
      typeof window !== "undefined" &&
      window.location.hostname === "localhost"
    ) {
      console.error("ErrorBoundary caught an error:", error, errorInfo);
    }

    this.setState({
      error,
      errorInfo,
    });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  override render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <Container maxWidth="md">
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              minHeight: "80vh",
              textAlign: "center",
            }}
          >
            <Card sx={{ width: "100%", maxWidth: 600 }}>
              <CardContent sx={{ p: 4 }}>
                <ErrorOutline
                  sx={{
                    fontSize: 80,
                    color: "error.main",
                    mb: 2,
                  }}
                />

                <Typography
                  variant="h4"
                  component="h1"
                  gutterBottom
                  sx={{ fontWeight: 600 }}
                >
                  Something went wrong
                </Typography>

                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mb: 3 }}
                >
                  We're sorry, but something unexpected happened. Please try
                  refreshing the page or contact support if the problem
                  persists.
                </Typography>

                {typeof window !== "undefined" &&
                  window.location.hostname === "localhost" &&
                  this.state.error && (
                    <Card
                      variant="outlined"
                      sx={{ mb: 3, p: 2, textAlign: "left" }}
                    >
                      <Typography
                        variant="subtitle2"
                        gutterBottom
                        color="error"
                      >
                        Error Details (Development Only):
                      </Typography>
                      <Typography
                        variant="body2"
                        component="pre"
                        sx={{
                          fontFamily: "monospace",
                          fontSize: "0.75rem",
                          color: "error.main",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {this.state.error.message}
                        {this.state.errorInfo?.componentStack && (
                          <>
                            {"\n\nComponent Stack:"}
                            {this.state.errorInfo.componentStack}
                          </>
                        )}
                      </Typography>
                    </Card>
                  )}

                <Box
                  sx={{
                    display: "flex",
                    gap: 2,
                    justifyContent: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <Button
                    variant="contained"
                    startIcon={<Refresh />}
                    onClick={this.handleRetry}
                    sx={{ minWidth: 120 }}
                  >
                    Try Again
                  </Button>

                  <Button
                    variant="outlined"
                    startIcon={<BugReport />}
                    onClick={this.handleReload}
                    sx={{ minWidth: 120 }}
                  >
                    Reload Page
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Container>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
