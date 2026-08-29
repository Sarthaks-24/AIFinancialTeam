import { Avatar, Box, Typography, keyframes } from "@mui/material";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import RecordVoiceOverOutlinedIcon from "@mui/icons-material/RecordVoiceOverOutlined";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";

const PRESENCE = {
  online: { label: "Online", color: "success", detail: "Here when you need me" },
  listening: { label: "Listening", color: "error", detail: "I'm listening..." },
  thinking: { label: "Thinking", color: "warning", detail: "Processing..." },
  speaking: { label: "Speaking", color: "primary", detail: "Answering..." },
};

function PresenceIcon({ state, sx }) {
  if (state === "listening") return <GraphicEqIcon sx={sx} />;
  if (state === "speaking") return <RecordVoiceOverOutlinedIcon sx={sx} />;
  return <SmartToyOutlinedIcon sx={sx} />;
}

// Subtle pulsing animation for idle
const pulseOnline = keyframes`
  0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4); }
  70% { box-shadow: 0 0 0 15px rgba(76, 175, 80, 0); }
  100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
`;

// Active pulsing for listening/thinking
const pulseActive = keyframes`
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.4); }
  50% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(25, 118, 210, 0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(25, 118, 210, 0); }
`;

export default function AssistantPresence({ name = "Ava", state = "online" }) {
  const presence = PRESENCE[state] || PRESENCE.online;
  const isIdle = state === "online";

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 4 }}>
      <Box
        sx={{
          position: "relative",
          mb: 3,
          animation: `${isIdle ? pulseOnline : pulseActive} ${isIdle ? '3s' : '1.5s'} infinite ease-in-out`,
          borderRadius: "50%",
        }}
      >
        <Avatar
          sx={{
            width: 96,
            height: 96,
            bgcolor: `${presence.color}.main`,
            transition: 'background-color 0.3s ease',
          }}
        >
          <PresenceIcon state={state} sx={{ fontSize: 48 }} />
        </Avatar>
      </Box>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {name}
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ opacity: 0.8 }}>
        {presence.detail}
      </Typography>
    </Box>
  );
}
