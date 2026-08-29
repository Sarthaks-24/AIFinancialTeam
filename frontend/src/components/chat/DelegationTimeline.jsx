import { Box, Chip, CircularProgress, Collapse, Stack, Typography } from "@mui/material";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import ErrorOutlinedIcon from "@mui/icons-material/ErrorOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { keyframes } from "@mui/system";

/**
 * DelegationTimeline — renders delegation handoff events in two modes:
 *
 * 1. **Live** (isComplete === false, delegations array has items):
 *    Shows each from → to step with a pulsing indicator and activity label.
 *
 * 2. **Collapsed** (isComplete === true, or contributors-only):
 *    Concise one-liner like "consulted Vega and Nova".
 *
 * When no delegation events were received but `contributors` exist,
 * it renders only the collapsed summary — no pretend animation.
 */

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
`;

const STATUS_ICON = {
  started: (
    <CircularProgress
      size={14}
      thickness={5}
      sx={{ animation: `${pulse} 1.5s ease-in-out infinite` }}
    />
  ),
  completed: <CheckCircleOutlinedIcon sx={{ fontSize: 16, color: "success.main" }} />,
  failed: <ErrorOutlinedIcon sx={{ fontSize: 16, color: "error.main" }} />,
};

function formatContributorsList(names) {
  if (!names || names.length === 0) return "";
  if (names.length === 1) return names[0];
  return names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
}

function DelegationStep({ step }) {
  const icon = STATUS_ICON[step.status] || STATUS_ICON.started;

  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="center"
      sx={{
        py: 0.5,
        transition: "opacity 0.3s ease",
        opacity: step.status === "completed" ? 0.7 : 1,
      }}
    >
      {icon}
      <Chip
        label={step.from}
        size="small"
        variant="outlined"
        sx={{ fontWeight: 600, fontSize: "0.7rem", height: 22 }}
      />
      <ArrowForwardIcon sx={{ fontSize: 14, color: "text.disabled" }} />
      <Chip
        label={step.to}
        size="small"
        color={step.status === "failed" ? "error" : "secondary"}
        variant="outlined"
        sx={{ fontWeight: 600, fontSize: "0.7rem", height: 22 }}
      />
      {step.activity && step.status === "started" && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            ml: 0.5,
            fontStyle: "italic",
            animation: `${pulse} 2s ease-in-out infinite`,
          }}
        >
          {step.activity}
        </Typography>
      )}
      {step.status === "failed" && step.reason && (
        <Typography variant="caption" color="error.main" sx={{ ml: 0.5 }}>
          {step.reason}
        </Typography>
      )}
    </Stack>
  );
}

function CollapsedSummary({ names }) {
  if (!names || names.length === 0) return null;

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
      <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
        consulted
      </Typography>
      {names.map((name) => (
        <Chip
          key={name}
          label={name}
          size="small"
          variant="outlined"
          color="secondary"
          sx={{ fontWeight: 500, fontSize: "0.7rem" }}
        />
      ))}
    </Stack>
  );
}

export default function DelegationTimeline({ delegations = [], contributors = [], isComplete = false }) {
  const hasLiveEvents = delegations.length > 0;

  // After completion, collapse to a summary of unique delegate names.
  if (isComplete || !hasLiveEvents) {
    const names = hasLiveEvents
      ? [...new Set(delegations.map((step) => step.to))]
      : contributors;
    return <CollapsedSummary names={names} />;
  }

  // Live mode — show each delegation step.
  return (
    <Collapse in timeout={300}>
      <Box sx={{ mb: 1.5, pl: 0.5 }}>
        {delegations.map((step, index) => (
          <DelegationStep key={`${step.from}-${step.to}-${index}`} step={step} />
        ))}
      </Box>
    </Collapse>
  );
}
