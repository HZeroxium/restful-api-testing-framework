import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Box,
  Typography,
} from "@mui/material";
import {
  Dashboard,
  FolderOpen,
  Upload,
  Science,
  List as ListIcon,
  BugReport,
  Code,
  DataObject,
  History,
  PlayArrow,
  VerifiedUser,
  ExpandLess,
  ExpandMore,
  GroupWork,
} from "@mui/icons-material";
import HealthIndicator from "@/components/common/HealthIndicator";

const DRAWER_WIDTH = 280;

interface NavigationItem {
  id: string;
  label: string;
  path?: string;
  icon: React.ReactNode;
  children?: NavigationItem[];
}

const navigationItems: NavigationItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/",
    icon: <Dashboard />,
  },
  {
    id: "datasets",
    label: "Datasets",
    icon: <FolderOpen />,
    children: [
      {
        id: "datasets-list",
        label: "All Datasets",
        path: "/datasets",
        icon: <ListIcon />,
      },
      {
        id: "datasets-upload",
        label: "Upload Spec",
        path: "/datasets/upload",
        icon: <Upload />,
      },
    ],
  },
  {
    id: "testing",
    label: "Testing",
    icon: <Science />,
    children: [
      {
        id: "endpoints",
        label: "Endpoints",
        path: "/endpoints",
        icon: <ListIcon />,
      },
      {
        id: "constraints",
        label: "Constraints",
        path: "/constraints",
        icon: <BugReport />,
      },
      {
        id: "validation-scripts",
        label: "Validation Scripts",
        path: "/validation-scripts",
        icon: <Code />,
      },
      {
        id: "test-data",
        label: "Test Data",
        path: "/test-data",
        icon: <DataObject />,
      },
    ],
  },
  {
    id: "history",
    label: "History",
    icon: <History />,
    children: [
      {
        id: "executions",
        label: "Executions",
        path: "/executions",
        icon: <PlayArrow />,
      },
      {
        id: "verification",
        label: "Verification",
        path: "/verification",
        icon: <VerifiedUser />,
      },
    ],
  },
  {
    id: "batch-operations",
    label: "Batch Operations",
    path: "/batch-operations",
    icon: <GroupWork />,
  },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedItems, setExpandedItems] = useState<string[]>([
    "datasets",
    "testing",
    "history",
  ]);

  const handleToggleExpand = (itemId: string) => {
    setExpandedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleNavigate = (path: string) => {
    navigate(path);
    onClose();
  };

  const isActive = (path?: string) => {
    if (!path) return false;
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  const isExpanded = (itemId: string) => expandedItems.includes(itemId);

  const renderNavigationItem = (item: NavigationItem, level = 0) => {
    const hasChildren = item.children && item.children.length > 0;
    const expanded = isExpanded(item.id);
    const active = isActive(item.path);

    return (
      <React.Fragment key={item.id}>
        <ListItem disablePadding>
          <ListItemButton
            onClick={() => {
              if (hasChildren) {
                handleToggleExpand(item.id);
              } else if (item.path) {
                handleNavigate(item.path);
              }
            }}
            selected={active}
            sx={{
              pl: 2 + level * 2,
              minHeight: 48,
              "&.Mui-selected": {
                backgroundColor: "primary.main",
                color: "primary.contrastText",
                "& .MuiListItemIcon-root": {
                  color: "primary.contrastText",
                },
                "&:hover": {
                  backgroundColor: "primary.dark",
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                color: active ? "primary.contrastText" : "text.secondary",
                minWidth: 40,
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                fontSize: "0.875rem",
                fontWeight: active ? 600 : 400,
              }}
            />
            {hasChildren && (expanded ? <ExpandLess /> : <ExpandMore />)}
          </ListItemButton>
        </ListItem>

        {hasChildren && (
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <List component="div" disablePadding>
              {item.children!.map((child) =>
                renderNavigationItem(child, level + 1)
              )}
            </List>
          </Collapse>
        )}
      </React.Fragment>
    );
  };

  const drawerContent = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <Box sx={{ p: 3, borderBottom: 1, borderColor: "divider" }}>
        <Typography
          variant="h6"
          component="div"
          sx={{ fontWeight: 600, color: "primary.main" }}
        >
          API Testing Framework
        </Typography>
        <Typography variant="body2" color="text.secondary">
          RESTful API Testing Tool
        </Typography>
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflow: "auto" }}>
        <List sx={{ pt: 1 }}>
          {navigationItems.map((item) => renderNavigationItem(item))}
        </List>
      </Box>

      {/* Footer */}
      <Box sx={{ p: 2, borderTop: 1, borderColor: "divider" }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 1,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            System Status:
          </Typography>
          <HealthIndicator />
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          align="center"
          sx={{ display: "block" }}
        >
          Version 0.1.0
        </Typography>
      </Box>
    </Box>
  );

  return (
    <>
      {/* Desktop Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            position: "relative",
            height: "100vh",
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Mobile Drawer */}
      <Drawer
        variant="temporary"
        open={open}
        onClose={onClose}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
};

export default Sidebar;
