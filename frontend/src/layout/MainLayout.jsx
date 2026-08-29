import { useState } from "react";
import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";

import Sidebar from "../components/Sidebar/Sidebar";
import TopNavbar from "../components/Navbar/TopNavbar";

export default function MainLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <Box sx={{ flexGrow: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopNavbar onMenuClick={() => setMobileOpen(true)} />

        <Box
          component="main"
          sx={{
            p: { xs: 2, sm: 3 },
            flexGrow: 1,
            maxWidth: "100%",
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}