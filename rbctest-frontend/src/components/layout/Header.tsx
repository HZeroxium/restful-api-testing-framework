import React from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Breadcrumbs,
  Link,
  Box,
  Avatar,
} from "@mui/material";
import { Menu as MenuIcon, Home, ChevronRight } from "@mui/icons-material";

interface HeaderProps {
  title: string;
  onMenuClick: () => void;
  breadcrumbs?: Array<{
    label: string;
    path?: string;
  }>;
}

const Header: React.FC<HeaderProps> = ({
  title,
  onMenuClick,
  breadcrumbs = [],
}) => {
  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        backgroundColor: "background.paper",
        color: "text.primary",
      }}
    >
      <Toolbar>
        {/* Mobile Menu Button */}
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{
            mr: 2,
            display: { md: "none" },
            color: "text.primary",
          }}
        >
          <MenuIcon />
        </IconButton>

        {/* Page Title */}
        <Typography
          variant="h6"
          component="h1"
          sx={{
            flexGrow: 1,
            fontWeight: 600,
            color: "text.primary",
          }}
        >
          {title}
        </Typography>

        {/* Breadcrumbs */}
        {breadcrumbs.length > 0 && (
          <Box
            sx={{
              display: { xs: "none", sm: "flex" },
              alignItems: "center",
              mr: 2,
            }}
          >
            <Breadcrumbs
              separator={<ChevronRight fontSize="small" />}
              sx={{
                "& .MuiBreadcrumbs-separator": {
                  color: "text.secondary",
                },
              }}
            >
              <Link
                component="button"
                variant="body2"
                onClick={() => (window.location.href = "/")}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  textDecoration: "none",
                  color: "text.secondary",
                  "&:hover": {
                    color: "primary.main",
                  },
                }}
              >
                <Home fontSize="small" sx={{ mr: 0.5 }} />
                Home
              </Link>
              {breadcrumbs.map((crumb, index) => (
                <Typography
                  key={index}
                  variant="body2"
                  color={
                    index === breadcrumbs.length - 1
                      ? "text.primary"
                      : "text.secondary"
                  }
                  sx={{
                    fontWeight: index === breadcrumbs.length - 1 ? 500 : 400,
                  }}
                >
                  {crumb.label}
                </Typography>
              ))}
            </Breadcrumbs>
          </Box>
        )}

        {/* User Avatar (placeholder for future user management) */}
        <Avatar
          sx={{
            width: 32,
            height: 32,
            bgcolor: "primary.main",
            fontSize: "0.875rem",
          }}
        >
          U
        </Avatar>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
