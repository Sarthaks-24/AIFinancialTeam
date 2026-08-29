import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";

import DashboardIcon from "@mui/icons-material/DashboardOutlined";
import AssessmentIcon from "@mui/icons-material/AssessmentOutlined";
import DescriptionIcon from "@mui/icons-material/DescriptionOutlined";
import TaskIcon from "@mui/icons-material/TaskOutlined";
import SmartToyIcon from "@mui/icons-material/SmartToyOutlined";
import HistoryIcon from "@mui/icons-material/HistoryOutlined";
import SettingsIcon from "@mui/icons-material/SettingsOutlined";
import CurrencyRupeeIcon from "@mui/icons-material/CurrencyRupee";

import { Link, useLocation } from "react-router-dom";

export const DRAWER_WIDTH = 260;

const menu = [
  { text: "Dashboard", path: "/dashboard", icon: <DashboardIcon /> },
  { text: "KPI", path: "/kpi", icon: <AssessmentIcon /> },
  { text: "Reports", path: "/reports", icon: <DescriptionIcon /> },
  { text: "Tasks", path: "/tasks", icon: <TaskIcon /> },
  { text: "Talk", path: "/talk", icon: <SmartToyIcon /> },
  { text: "History", path: "/history", icon: <HistoryIcon /> },
  { text: "Financial Data", path: "/financial-data", icon: <CurrencyRupeeIcon /> },
  { text: "Settings", path: "/settings", icon: <SettingsIcon /> },
  
];

function SidebarContent({ onNavigate }) {
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box sx={{ px: 3, py: 2.5 }}>
        <Typography variant="h6" sx={{ fontWeight: 800, color: "primary.main" }}>
          💼 AI Financial Team
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Financial intelligence
        </Typography>
      </Box>

      <Divider />

      <List sx={{ px: 1, py: 1.5, flexGrow: 1 }}>
        {menu.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.text}
              component={Link}
              to={item.path}
              selected={selected}
              onClick={onNavigate}
              sx={{
                mb: 0.5,
                color: selected ? "primary.main" : "text.primary",
                "&.Mui-selected": {
                  bgcolor: "primary.main",
                  color: "#fff",
                  "&:hover": { bgcolor: "primary.dark" },
                  "& .MuiListItemIcon-root": { color: "#fff" },
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 40,
                  color: selected ? "#fff" : "text.secondary",
                }}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.text}
                primaryTypographyProps={{ fontWeight: selected ? 600 : 500, fontSize: 14 }}
              />
            </ListItemButton>
          );
        })}
      </List>

      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary">
          v1.0 · AI Financial Team
        </Typography>
      </Box>
    </Box>
  );
}

export default function Sidebar({ mobileOpen, onClose }) {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));

  if (isDesktop) {
    return (
      <Box
        component="nav"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          height: "100vh",
          position: "sticky",
          top: 0,
          bgcolor: "background.paper",
          borderRight: "1px solid #E5E9EF",
        }}
      >
        <SidebarContent />
      </Box>
    );
  }

  return (
    <Drawer
      variant="temporary"
      open={mobileOpen}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={{
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
        },
      }}
    >
      <SidebarContent onNavigate={onClose} />
    </Drawer>
  );
}