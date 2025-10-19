import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  TextField,
  Button,
  Typography,
  MenuItem,
  Tabs,
  Tab,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Alert,
  FormControl,
  InputLabel,
  Select,
} from "@mui/material";

import Grid from "@mui/material/Grid";

import {
  Send as SendIcon,
  History as HistoryIcon,
  Settings as SettingsIcon,
  Delete as DeleteIcon,
  PlayArrow as PlayIcon,
} from "@mui/icons-material";
import { useExecuteMutation } from "@/services/api/playgroundApi";
import { CodeViewer } from "@/components/common/CodeViewer";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

interface Environment {
  id: string;
  name: string;
  baseUrl: string;
  headers: Record<string, string>;
  token?: string;
}

interface RequestHistory {
  id: string;
  timestamp: number;
  method: string;
  url: string;
  statusCode: number;
  elapsed: number;
}

const PlaygroundPage: React.FC = () => {
  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // Request state
  const [method, setMethod] = useState<string>("GET");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [path, setPath] = useState<string>("");
  const [params, setParams] = useState<string>("{}");
  const [headers, setHeaders] = useState<string>("{}");
  const [body, setBody] = useState<string>("{}");
  const [token, setToken] = useState<string>("");
  const [timeout, setTimeout] = useState<number>(15);
  const [retries, setRetries] = useState<number>(2);

  // Environment state
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>("");
  const [environmentDialogOpen, setEnvironmentDialogOpen] = useState(false);
  const [newEnvironment, setNewEnvironment] = useState<Partial<Environment>>({
    name: "",
    baseUrl: "",
    headers: {},
    token: "",
  });

  // History state
  const [history, setHistory] = useState<RequestHistory[]>([]);
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);

  // API state
  const [execute, { isLoading, data, error }] = useExecuteMutation();

  // Load data from localStorage on mount
  useEffect(() => {
    const savedEnvironments = localStorage.getItem("playground_environments");
    const savedHistory = localStorage.getItem("playground_history");
    const savedSelectedEnv = localStorage.getItem("playground_selected_env");

    if (savedEnvironments) {
      setEnvironments(JSON.parse(savedEnvironments));
    }
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
    if (savedSelectedEnv) {
      setSelectedEnvironment(savedSelectedEnv);
      const env = JSON.parse(savedSelectedEnv);
      if (env) {
        setBaseUrl(env.baseUrl || "");
        setHeaders(JSON.stringify(env.headers || {}, null, 2));
        setToken(env.token || "");
      }
    }
  }, []);

  // Save to localStorage when data changes
  useEffect(() => {
    localStorage.setItem(
      "playground_environments",
      JSON.stringify(environments)
    );
  }, [environments]);

  useEffect(() => {
    localStorage.setItem("playground_history", JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    localStorage.setItem(
      "playground_selected_env",
      JSON.stringify(selectedEnvironment)
    );
  }, [selectedEnvironment]);

  const parseJson = (text: string) => {
    try {
      return text ? JSON.parse(text) : undefined;
    } catch {
      return undefined;
    }
  };

  const onSend = async () => {
    const requestData = {
      method,
      base_url: baseUrl,
      path,
      params: parseJson(params) || {},
      headers: parseJson(headers) || {},
      body: method === "GET" ? undefined : parseJson(body),
      token: token || undefined,
      timeout,
      retries,
    };

    try {
      const result = await execute(requestData).unwrap();

      // Add to history
      const historyItem: RequestHistory = {
        id: Date.now().toString(),
        timestamp: Date.now(),
        method,
        url: result.url,
        statusCode: result.status_code,
        elapsed: result.elapsed_ms,
      };
      setHistory((prev) => [historyItem, ...prev.slice(0, 49)]); // Keep last 50
    } catch (err) {
      console.error("Request failed:", err);
    }
  };

  const handleEnvironmentChange = (envId: string) => {
    const env = environments.find((e) => e.id === envId);
    if (env) {
      setSelectedEnvironment(envId);
      setBaseUrl(env.baseUrl);
      setHeaders(JSON.stringify(env.headers, null, 2));
      setToken(env.token || "");
    }
  };

  const saveEnvironment = () => {
    if (!newEnvironment.name || !newEnvironment.baseUrl) return;

    const env: Environment = {
      id: Date.now().toString(),
      name: newEnvironment.name,
      baseUrl: newEnvironment.baseUrl,
      headers: newEnvironment.headers || {},
      token: newEnvironment.token,
    };

    setEnvironments((prev) => [...prev, env]);
    setNewEnvironment({ name: "", baseUrl: "", headers: {}, token: "" });
    setEnvironmentDialogOpen(false);
  };

  const deleteEnvironment = (envId: string) => {
    setEnvironments((prev) => prev.filter((e) => e.id !== envId));
    if (selectedEnvironment === envId) {
      setSelectedEnvironment("");
    }
  };

  const replayRequest = (historyItem: RequestHistory) => {
    // Extract method and URL from history
    const urlParts = historyItem.url.split("/");
    const baseUrl = urlParts.slice(0, 3).join("/");
    const path = "/" + urlParts.slice(3).join("/");

    setMethod(historyItem.method);
    setBaseUrl(baseUrl);
    setPath(path);
  };

  const TabPanel: React.FC<{
    children: React.ReactNode;
    index: number;
    value: number;
  }> = ({ children, value, index }) => (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
    </div>
  );

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          API Playground
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<HistoryIcon />}
            onClick={() => setHistoryDialogOpen(true)}
          >
            History ({history.length})
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setEnvironmentDialogOpen(true)}
          >
            Environments
          </Button>
        </Box>
      </Box>

      <Card>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
        >
          <Tab label="Request" />
          <Tab label="Headers" />
          <Tab label="Body" />
          <Tab label="Options" />
        </Tabs>

        {/* Request Tab */}
        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 2 }}>
              <FormControl fullWidth>
                <InputLabel>Method</InputLabel>
                <Select
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                >
                  {HTTP_METHODS.map((m) => (
                    <MenuItem key={m} value={m}>
                      {m}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Base URL"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                fullWidth
                placeholder="https://api.example.com"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                label="Path"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                fullWidth
                placeholder="/v1/users"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <Button
                variant="contained"
                fullWidth
                startIcon={<SendIcon />}
                onClick={onSend}
                disabled={isLoading || !baseUrl}
              >
                {isLoading ? "Sending..." : "Send"}
              </Button>
            </Grid>
          </Grid>

          <Box sx={{ mt: 2 }}>
            <TextField
              label="Query Parameters (JSON)"
              value={params}
              onChange={(e) => setParams(e.target.value)}
              multiline
              rows={4}
              fullWidth
              placeholder='{"page": 1, "limit": 10}'
            />
          </Box>
        </TabPanel>

        {/* Headers Tab */}
        <TabPanel value={activeTab} index={1}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Headers (JSON)"
                value={headers}
                onChange={(e) => setHeaders(e.target.value)}
                multiline
                rows={8}
                fullWidth
                placeholder='{"Content-Type": "application/json", "Accept": "application/json"}'
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Bearer Token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                fullWidth
                placeholder="Enter your Bearer token"
                type="password"
              />
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1, display: "block" }}
              >
                Token will be automatically added to Authorization header
              </Typography>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Body Tab */}
        <TabPanel value={activeTab} index={2}>
          {method !== "GET" ? (
            <TextField
              label="Request Body (JSON)"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              multiline
              rows={12}
              fullWidth
              placeholder='{"name": "John Doe", "email": "john@example.com"}'
            />
          ) : (
            <Alert severity="info">
              GET requests don't typically have a request body.
            </Alert>
          )}
        </TabPanel>

        {/* Options Tab */}
        <TabPanel value={activeTab} index={3}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Timeout (seconds)"
                type="number"
                value={timeout}
                onChange={(e) => setTimeout(Number(e.target.value))}
                fullWidth
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                label="Retries"
                type="number"
                value={retries}
                onChange={(e) => setRetries(Number(e.target.value))}
                fullWidth
              />
            </Grid>
          </Grid>
        </TabPanel>
      </Card>

      {/* Response */}
      {data && (
        <Card sx={{ p: 2 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6">Response</Typography>
            <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
              <Chip
                label={`${data.status_code}`}
                color={
                  data.status_code >= 200 && data.status_code < 300
                    ? "success"
                    : "error"
                }
              />
              <Typography variant="body2" color="text.secondary">
                {data.elapsed_ms.toFixed(1)} ms
              </Typography>
            </Box>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Headers
            </Typography>
            <CodeViewer
              code={JSON.stringify(data.headers, null, 2)}
              language="json"
            />
          </Box>

          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Body
            </Typography>
            <CodeViewer
              code={JSON.stringify(data.body, null, 2)}
              language="json"
            />
          </Box>
        </Card>
      )}

      {error && (
        <Alert severity="error">
          Failed to execute request: {error.toString()}
        </Alert>
      )}

      {/* Environment Dialog */}
      <Dialog
        open={environmentDialogOpen}
        onClose={() => setEnvironmentDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Manage Environments</DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Create New Environment
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Name"
                  value={newEnvironment.name || ""}
                  onChange={(e) =>
                    setNewEnvironment((prev) => ({
                      ...prev,
                      name: e.target.value,
                    }))
                  }
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Base URL"
                  value={newEnvironment.baseUrl || ""}
                  onChange={(e) =>
                    setNewEnvironment((prev) => ({
                      ...prev,
                      baseUrl: e.target.value,
                    }))
                  }
                  fullWidth
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Token"
                  value={newEnvironment.token || ""}
                  onChange={(e) =>
                    setNewEnvironment((prev) => ({
                      ...prev,
                      token: e.target.value,
                    }))
                  }
                  fullWidth
                  type="password"
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Button variant="contained" onClick={saveEnvironment} fullWidth>
                  Save Environment
                </Button>
              </Grid>
            </Grid>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="h6" gutterBottom>
            Saved Environments
          </Typography>
          <List>
            {environments.map((env) => (
              <ListItem key={env.id}>
                <ListItemText primary={env.name} secondary={env.baseUrl} />
                <ListItemSecondaryAction>
                  <IconButton onClick={() => handleEnvironmentChange(env.id)}>
                    <PlayIcon />
                  </IconButton>
                  <IconButton onClick={() => deleteEnvironment(env.id)}>
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEnvironmentDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* History Dialog */}
      <Dialog
        open={historyDialogOpen}
        onClose={() => setHistoryDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Request History</DialogTitle>
        <DialogContent>
          <List>
            {history.map((item) => (
              <ListItem key={item.id}>
                <ListItemText
                  primary={`${item.method} ${item.url}`}
                  secondary={`${new Date(item.timestamp).toLocaleString()} • ${
                    item.statusCode
                  } • ${item.elapsed.toFixed(1)}ms`}
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={() => replayRequest(item)}>
                    <PlayIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PlaygroundPage;
