import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Paper,
  Stack,
  Avatar,
  Divider,
  Button,
  Chip,
} from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";

import { useAuth } from "../../context/AuthContext";

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const initials = (user?.username || "U").slice(0, 1).toUpperCase();

  return (
    <Box>
      <Typography variant="h4" mb={3}>Settings</Typography>

      <Paper sx={{ p: { xs: 2.5, sm: 3 }, maxWidth: 520 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <Avatar sx={{ width: 56, height: 56, bgcolor: "primary.main", fontSize: 22, fontWeight: 700 }}>
            {initials}
          </Avatar>
          <Box>
            <Typography variant="h6">{user?.username || "User"}</Typography>
            <Stack direction="row" spacing={1} mt={0.5} flexWrap="wrap" useFlexGap>
              {user?.groups?.length > 0 ? (
                user.groups.map((g) => <Chip key={g} size="small" label={g} />)
              ) : (
                <Chip size="small" label="Member" variant="outlined" />
              )}
            </Stack>
          </Box>
        </Stack>

        <Divider sx={{ my: 3 }} />

        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Account
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Manage your session for the AI Financial Team workspace. More preferences (notifications, theme) are coming soon.
        </Typography>

        <Button
          variant="outlined"
          color="error"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
        >
          Log out
        </Button>
      </Paper>
    </Box>
  );
}