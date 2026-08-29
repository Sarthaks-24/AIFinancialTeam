import { useState } from "react";
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import MenuIcon from "@mui/icons-material/Menu";
import LogoutIcon from "@mui/icons-material/Logout";
import SettingsIcon from "@mui/icons-material/Settings";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const titles = {
  "/dashboard": "Dashboard",
  "/kpi": "KPI Overview",
  "/reports": "Reports",
  "/tasks": "Tasks",
  "/chat": "Talk",
  "/talk": "Talk",
  "/history": "Query History",
  "/settings": "Settings",
};

export default function TopNavbar({ onMenuClick }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const pageTitle = titles[location.pathname] || "AI Financial Team";

  function handleLogout() {
    setAnchorEl(null);
    logout();
    navigate("/login");
  }

  const initials = (user?.username || "U").slice(0, 1).toUpperCase();

  return (
    <AppBar
      position="sticky"
      elevation={0}
      color="inherit"
      sx={{ borderBottom: "1px solid #E5E9EF", top: 0, zIndex: (t) => t.zIndex.drawer + 1 }}
    >
      <Toolbar sx={{ gap: 1 }}>
        {isMobile && (
          <IconButton edge="start" onClick={onMenuClick} aria-label="Open menu">
            <MenuIcon />
          </IconButton>
        )}

        <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1 }}>
          {pageTitle}
        </Typography>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Avatar
            onClick={(e) => setAnchorEl(e.currentTarget)}
            sx={{
              width: 36,
              height: 36,
              bgcolor: "primary.main",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {initials}
          </Avatar>
        </Box>

        <Menu anchorEl={anchorEl} open={open} onClose={() => setAnchorEl(null)}>
          <Box sx={{ px: 2, py: 1 }}>
            <Typography variant="subtitle2" fontWeight={700}>
              {user?.username || "User"}
            </Typography>
            {user?.groups?.length > 0 && (
              <Typography variant="caption" color="text.secondary">
                {user.groups.join(", ")}
              </Typography>
            )}
          </Box>
          <Divider />
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              navigate("/settings");
            }}
          >
            <SettingsIcon fontSize="small" sx={{ mr: 1.5 }} />
            Settings
          </MenuItem>
          <MenuItem onClick={handleLogout}>
            <LogoutIcon fontSize="small" sx={{ mr: 1.5 }} />
            Log out
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
