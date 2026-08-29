import {
  Avatar,
  Box,
  Button,
  Divider,
  Drawer,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import CheckIcon from "@mui/icons-material/Check";

export default function ExpertTeamPanel({ open, specialists, activeSpecialist, onClose, onAskDirectly }) {
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: "100%", sm: 440 }, bgcolor: "#fbfcfe" } }}
    >
      <Box sx={{ p: { xs: 2.5, sm: 3.5 }, pb: 2.5 }}>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={2}>
          <Box>
            <Typography variant="overline" color="primary.main" fontWeight={800} letterSpacing={1.2}>
              TALK
            </Typography>
            <Typography variant="h5" fontWeight={750} sx={{ mt: 0.25 }}>
              Choose your agent
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75, lineHeight: 1.6 }}>
              Switch to a specialist for a new conversation.
            </Typography>
          </Box>
          <IconButton onClick={onClose} aria-label="Close experts panel">
            <CloseIcon />
          </IconButton>
        </Stack>
      </Box>
      <Divider />
      <Stack spacing={1.25} sx={{ p: { xs: 2, sm: 2.5 }, overflowY: "auto" }}>
        {specialists.map((expert) => {
          const isActive = expert.name === activeSpecialist;
          return (
            <Box
              key={expert.name}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                p: 1.5,
                border: "1px solid",
                borderColor: isActive ? expert.color || "primary.main" : "divider",
                borderRadius: 3,
                bgcolor: isActive ? `${expert.color || "#1976d2"}12` : "background.paper",
                transition: "transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease",
                "&:hover": { transform: "translateY(-2px)", boxShadow: "0 8px 18px rgba(15, 23, 42, 0.08)" },
              }}
            >
              <Avatar sx={{ width: 42, height: 42, bgcolor: expert.color || "primary.main", flexShrink: 0 }}>
                <SmartToyOutlinedIcon fontSize="small" />
              </Avatar>
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Stack direction="row" alignItems="center" spacing={0.75}>
                  <Typography fontWeight={750}>{expert.name}</Typography>
                  {isActive && <CheckIcon color="success" sx={{ fontSize: 17 }} aria-label="Current agent" />}
                </Stack>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontWeight: 700, mt: 0.1 }}>
                  {expert.title || expert.role || "Specialist"}
                </Typography>
                {expert.description && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.45, lineHeight: 1.45 }}>
                    {expert.description}
                  </Typography>
                )}
              </Box>
              <Button
                size="small"
                variant={isActive ? "text" : "contained"}
                disabled={isActive}
                onClick={() => onAskDirectly(expert.name)}
                sx={{ minWidth: 72, flexShrink: 0, textTransform: "none", fontWeight: 700 }}
              >
                {isActive ? "Current" : "Switch"}
              </Button>
            </Box>
          );
        })}
      </Stack>
    </Drawer>
  );
}
