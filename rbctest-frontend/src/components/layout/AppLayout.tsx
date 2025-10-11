import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Box, CssBaseline, Toolbar } from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";
import Header from "./Header";
import Sidebar from "./Sidebar";
import Breadcrumb from "../common/Breadcrumb";
import theme from "@/theme/theme";

const DRAWER_WIDTH = 280;

const AppLayout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  // Map current route to title + breadcrumbs
  const getPageInfo = () => {
    const path = location.pathname;
    let title = "Dashboard";
    let breadcrumbs: Array<{ label: string; path?: string }> = [];

    if (path === "/") title = "Dashboard";
    else if (path === "/datasets") {
      title = "Datasets";
      breadcrumbs = [{ label: "Datasets" }];
    } else if (path === "/datasets/upload") {
      title = "Upload OpenAPI Spec";
      breadcrumbs = [
        { label: "Datasets", path: "/datasets" },
        { label: "Upload Spec" },
      ];
    } else if (path.startsWith("/datasets/") && path !== "/datasets") {
      title = "Dataset Details";
      breadcrumbs = [
        { label: "Datasets", path: "/datasets" },
        { label: "Details" },
      ];
    } else if (path === "/endpoints") {
      title = "Endpoints";
      breadcrumbs = [{ label: "Endpoints" }];
    } else if (path.startsWith("/endpoints/") && path !== "/endpoints") {
      title = "Endpoint Details";
      breadcrumbs = [
        { label: "Endpoints", path: "/endpoints" },
        { label: "Details" },
      ];
    } else if (path === "/constraints") {
      title = "Constraints";
      breadcrumbs = [{ label: "Constraints" }];
    } else if (path === "/validation-scripts") {
      title = "Validation Scripts";
      breadcrumbs = [{ label: "Validation Scripts" }];
    } else if (path === "/test-data") {
      title = "Test Data";
      breadcrumbs = [{ label: "Test Data" }];
    } else if (path === "/executions") {
      title = "Executions";
      breadcrumbs = [{ label: "Executions" }];
    } else if (path.startsWith("/executions/") && path !== "/executions") {
      title = "Execution Details";
      breadcrumbs = [
        { label: "Executions", path: "/executions" },
        { label: "Details" },
      ];
    } else if (path === "/verification") {
      title = "Verification";
      breadcrumbs = [{ label: "Verification" }];
    }

    return { title, breadcrumbs };
  };

  const { title, breadcrumbs } = getPageInfo();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: "flex" }}>
        {/* Sidebar */}
        <Sidebar open={mobileOpen} onClose={handleDrawerToggle} />

        {/* Main content area */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
            minHeight: "100vh",
            backgroundColor: "background.default",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Header */}
          {/* <Header title={title} onMenuClick={handleDrawerToggle} /> */}

          {/* Toolbar spacer ensures content starts below fixed AppBar */}
          <Toolbar />

          {/* Content Area */}
          <Box
            sx={{
              flex: 1,
              px: { xs: 2, sm: 3, md: 4 },
              py: 0,
              overflow: "auto",
            }}
          >
            {breadcrumbs.length > 0 && <Breadcrumb items={breadcrumbs} />}
            <Outlet />
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default AppLayout;
