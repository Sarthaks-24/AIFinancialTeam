import { Box, keyframes, useTheme } from "@mui/material";

// --- Animations ---

const breathe = keyframes`
  0% { transform: scale(0.95); opacity: 0.8; filter: drop-shadow(0 0 15px rgba(var(--orb-color-rgb), 0.3)); }
  50% { transform: scale(1.05); opacity: 1; filter: drop-shadow(0 0 25px rgba(var(--orb-color-rgb), 0.6)); }
  100% { transform: scale(0.95); opacity: 0.8; filter: drop-shadow(0 0 15px rgba(var(--orb-color-rgb), 0.3)); }
`;

const radar = keyframes`
  0% { transform: scale(0.8); opacity: 1; box-shadow: 0 0 0 0 rgba(var(--orb-color-rgb), 0.7); }
  70% { transform: scale(1); opacity: 0.8; box-shadow: 0 0 0 30px rgba(var(--orb-color-rgb), 0); }
  100% { transform: scale(0.8); opacity: 1; box-shadow: 0 0 0 0 rgba(var(--orb-color-rgb), 0); }
`;

const rotateMorph = keyframes`
  0% { transform: rotate(0deg) scale(1) skew(0deg); border-radius: 50% 50% 50% 50%; }
  33% { transform: rotate(120deg) scale(1.05) skew(2deg); border-radius: 40% 60% 50% 50%; }
  66% { transform: rotate(240deg) scale(0.95) skew(-2deg); border-radius: 50% 50% 60% 40%; }
  100% { transform: rotate(360deg) scale(1) skew(0deg); border-radius: 50% 50% 50% 50%; }
`;

const waveform = keyframes`
  0%, 100% { transform: scaleY(1) scaleX(1); }
  20% { transform: scaleY(1.15) scaleX(0.95); }
  40% { transform: scaleY(0.9) scaleX(1.1); }
  60% { transform: scaleY(1.2) scaleX(0.9); }
  80% { transform: scaleY(0.95) scaleX(1.05); }
`;

export default function AgentOrb({ state = "idle", color = "#1976d2", size = 120 }) {
  const theme = useTheme();

  // Convert hex to rgb for css variables
  const hexToRgb = (hex) => {
    let r = 0, g = 0, b = 0;
    if (hex.length === 4) {
      r = parseInt(hex[1] + hex[1], 16);
      g = parseInt(hex[2] + hex[2], 16);
      b = parseInt(hex[3] + hex[3], 16);
    } else if (hex.length === 7) {
      r = parseInt(hex.substring(1, 3), 16);
      g = parseInt(hex.substring(3, 5), 16);
      b = parseInt(hex.substring(5, 7), 16);
    }
    return `${r}, ${g}, ${b}`;
  };

  const rgbColor = hexToRgb(color);

  // Define animation based on state
  let animationStyles = {};
  let innerStyles = {};

  switch (state) {
    case "listening":
      animationStyles = {
        animation: `${radar} 1.5s ease-out infinite`,
      };
      break;
    case "thinking":
    case "working":
      animationStyles = {
        animation: `${rotateMorph} 4s linear infinite`,
        background: `linear-gradient(135deg, ${color}, rgba(${rgbColor}, 0.3))`,
      };
      innerStyles = {
        animation: `${rotateMorph} 3s linear infinite reverse`,
        background: `radial-gradient(circle, rgba(255,255,255,0.8) 0%, rgba(${rgbColor},0) 70%)`,
      };
      break;
    case "speaking":
      animationStyles = {
        animation: `${waveform} 1s ease-in-out infinite`,
        boxShadow: `0 0 20px rgba(${rgbColor}, 0.5)`,
      };
      break;
    case "idle":
    default:
      animationStyles = {
        animation: `${breathe} 4s ease-in-out infinite`,
      };
      break;
  }

  return (
    <Box
      sx={{
        width: size + 48,
        height: size + 48,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "visible",
        zIndex: 1,
        "--orb-color-rgb": rgbColor,
        "& *": {
          "@media (prefers-reduced-motion: reduce)": {
            animation: "none !important",
            transform: "none !important",
          },
        },
      }}
    >
      {/* Outer Glow / Base Layer */}
      <Box
        sx={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: `radial-gradient(circle at 30% 30%, ${color}, rgba(${rgbColor}, 0.4) 70%, transparent 100%)`,
          boxShadow: `inset -10px -10px 20px rgba(0,0,0,0.1), 0 0 30px rgba(${rgbColor}, 0.3)`,
          filter: "blur(1px)",
          zIndex: 1,
          ...animationStyles,
        }}
      />

      {/* Inner Core */}
      <Box
        sx={{
          position: "absolute",
          width: size * 0.6,
          height: size * 0.6,
          borderRadius: "50%",
          background: `radial-gradient(circle at 40% 40%, rgba(255,255,255,0.9) 0%, rgba(${rgbColor}, 0.5) 60%, transparent 100%)`,
          filter: "blur(4px)",
          zIndex: 2,
          ...innerStyles,
        }}
      />

      {/* Surface Highlight for depth */}
      <Box
        sx={{
          position: "absolute",
          width: size,
          height: size,
          borderRadius: "50%",
          background: "linear-gradient(135deg, rgba(255,255,255,0.4) 0%, transparent 40%)",
          pointerEvents: "none",
          zIndex: 3,
        }}
      />
    </Box>
  );
}
