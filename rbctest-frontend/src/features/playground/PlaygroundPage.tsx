import React, { useState } from "react";
import {
  Box,
  Card,
  TextField,
  Button,
  Typography,
  MenuItem,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { useExecuteMutation } from "@/services/api/playgroundApi";
import { CodeViewer } from "@/components/common/CodeViewer";

const HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;

const PlaygroundPage: React.FC = () => {
  const [method, setMethod] = useState<string>("GET");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [path, setPath] = useState<string>("");
  const [params, setParams] = useState<string>("{}");
  const [headers, setHeaders] = useState<string>("{}");
  const [body, setBody] = useState<string>("{}");
  const [execute, { isLoading, data, error }] = useExecuteMutation();

  const parseJson = (text: string) => {
    try {
      return text ? JSON.parse(text) : undefined;
    } catch {
      return undefined;
    }
  };

  const onSend = async () => {
    await execute({
      method,
      base_url: baseUrl,
      path,
      params: parseJson(params) || {},
      headers: parseJson(headers) || {},
      body: method === "GET" ? undefined : parseJson(body),
    }).unwrap();
  };

  return (
    <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Playground
      </Typography>

      <Card sx={{ p: 2, display: "grid", gap: 2 }}>
        <Box sx={{ display: "flex", gap: 2 }}>
          <TextField
            select
            label="Method"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            sx={{ width: 140 }}
          >
            {HTTP_METHODS.map((m) => (
              <MenuItem key={m} value={m}>
                {m}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Base URL"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            fullWidth
          />
          <TextField
            label="Path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            fullWidth
          />
          <Button variant="contained" onClick={onSend} disabled={isLoading}>
            {isLoading ? "Sending..." : "Send"}
          </Button>
        </Box>

        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Params / Headers / Body</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box
              sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }}
            >
              <TextField
                label="Params (JSON)"
                value={params}
                onChange={(e) => setParams(e.target.value)}
                multiline
                minRows={6}
              />
              <TextField
                label="Headers (JSON)"
                value={headers}
                onChange={(e) => setHeaders(e.target.value)}
                multiline
                minRows={6}
              />
              {method !== "GET" && (
                <TextField
                  label="Body (JSON)"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  multiline
                  minRows={8}
                  sx={{ gridColumn: "1 / -1" }}
                />
              )}
            </Box>
          </AccordionDetails>
        </Accordion>
      </Card>

      {data && (
        <Card sx={{ p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {data.status_code} • {data.elapsed_ms.toFixed(1)} ms
          </Typography>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography>Response Headers</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <CodeViewer
                code={JSON.stringify(data.headers, null, 2)}
                language="json"
              />
            </AccordionDetails>
          </Accordion>
          <Typography variant="subtitle2" sx={{ mt: 2 }}>
            Body
          </Typography>
          <CodeViewer
            code={JSON.stringify(data.body, null, 2)}
            language="json"
          />
        </Card>
      )}

      {error && (
        <Typography color="error">Failed to execute request</Typography>
      )}
    </Box>
  );
};

export default PlaygroundPage;
