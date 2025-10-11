import React from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { tomorrow } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Box, Typography, Paper, IconButton, Tooltip } from "@mui/material";
import { ContentCopy, ExpandMore, ExpandLess } from "@mui/icons-material";
import { useState } from "react";

interface CodeViewerProps {
  code: string;
  language?: string;
  title?: string;
  maxHeight?: string | number;
  showLineNumbers?: boolean;
  copyable?: boolean;
  collapsible?: boolean;
  defaultExpanded?: boolean;
}

const CodeViewer: React.FC<CodeViewerProps> = ({
  code,
  language = "python",
  title,
  maxHeight = "400px",
  showLineNumbers = true,
  copyable = true,
  collapsible = false,
  defaultExpanded = true,
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  };

  const handleToggleExpanded = () => {
    setExpanded(!expanded);
  };

  return (
    <Paper
      elevation={1}
      sx={{
        borderRadius: 2,
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      {/* Header */}
      {(title || copyable || collapsible) && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 2,
            py: 1,
            backgroundColor: "grey.50",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontWeight: 500 }}
          >
            {title || `${language.toUpperCase()} Code`}
          </Typography>

          <Box sx={{ display: "flex", gap: 0.5 }}>
            {copyable && (
              <Tooltip title={copied ? "Copied!" : "Copy code"}>
                <IconButton size="small" onClick={handleCopy}>
                  <ContentCopy fontSize="small" />
                </IconButton>
              </Tooltip>
            )}

            {collapsible && (
              <Tooltip title={expanded ? "Collapse" : "Expand"}>
                <IconButton size="small" onClick={handleToggleExpanded}>
                  {expanded ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>
      )}

      {/* Code Content */}
      <Box
        sx={{
          maxHeight: expanded ? maxHeight : "200px",
          overflow: "auto",
          transition: "max-height 0.3s ease-in-out",
        }}
      >
        <SyntaxHighlighter
          language={language}
          style={tomorrow}
          showLineNumbers={showLineNumbers}
          customStyle={{
            margin: 0,
            padding: "16px",
            fontSize: "0.875rem",
            lineHeight: 1.5,
          }}
          lineNumberStyle={{
            color: "#666",
            marginRight: "16px",
            minWidth: "2em",
          }}
        >
          {code}
        </SyntaxHighlighter>
      </Box>
    </Paper>
  );
};

export default CodeViewer;
export { CodeViewer };
