import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Breadcrumbs, Typography, Link, Box, IconButton } from "@mui/material";
import { Home, ChevronRight, ArrowBack } from "@mui/icons-material";

interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbProps {
  items?: BreadcrumbItem[];
  showBackButton?: boolean;
  onBack?: () => void;
}

const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items = [],
  showBackButton = false,
  onBack,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        mb: 2,
        pt: 1,
      }}
    >
      {showBackButton && (
        <IconButton
          size="small"
          onClick={handleBack}
          sx={{
            mr: 1,
            color: "text.secondary",
            "&:hover": {
              color: "primary.main",
              backgroundColor: "primary.50",
            },
          }}
        >
          <ArrowBack fontSize="small" />
        </IconButton>
      )}

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
          onClick={() => navigate("/")}
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
        {items.map((item, index) => (
          <React.Fragment key={index}>
            {item.path ? (
              <Link
                component="button"
                variant="body2"
                onClick={() => navigate(item.path!)}
                sx={{
                  textDecoration: "none",
                  color: "text.secondary",
                  "&:hover": {
                    color: "primary.main",
                  },
                }}
              >
                {item.label}
              </Link>
            ) : (
              <Typography
                variant="body2"
                color="text.primary"
                sx={{ fontWeight: 500 }}
              >
                {item.label}
              </Typography>
            )}
          </React.Fragment>
        ))}
      </Breadcrumbs>
    </Box>
  );
};

export default Breadcrumb;
