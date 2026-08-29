import { Box, Typography, CircularProgress, Skeleton, Stack, Button } from "@mui/material";
import InboxIcon from "@mui/icons-material/InboxOutlined";
import LockIcon from "@mui/icons-material/LockOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";

export function PageLoader() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
      <CircularProgress />
    </Box>
  );
}

export function CardSkeletons({ count = 4 }) {
  return (
    <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton
          key={i}
          variant="rounded"
          width="100%"
          sx={{ flex: "1 1 220px", minWidth: 220 }}
          height={130}
        />
      ))}
    </Stack>
  );
}

export function EmptyState({ title = "Nothing here yet", subtitle }) {
  return (
    <Box
      sx={{
        textAlign: "center",
        py: 8,
        px: 2,
        color: "text.secondary",
      }}
    >
      <InboxIcon sx={{ fontSize: 48, mb: 1, opacity: 0.4 }} />
      <Typography variant="h6" color="text.primary">
        {title}
      </Typography>
      {subtitle && (
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {subtitle}
        </Typography>
      )}
    </Box>
  );
}

export function ErrorState({ status, onRetry }) {
  const isForbidden = status === 403;

  return (
    <Box
      sx={{
        textAlign: "center",
        py: 8,
        px: 2,
        color: "text.secondary",
      }}
    >
      <LockIcon sx={{ fontSize: 48, mb: 1, opacity: 0.4 }} />
      <Typography variant="h6" color="text.primary">
        {isForbidden ? "Access restricted" : "Couldn't load this page"}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, maxWidth: 360, mx: "auto" }}>
        {isForbidden
          ? "Your account role doesn't have permission to view this section. Ask an admin if you think this is a mistake."
          : "Something went wrong while fetching data. Check your connection and try again."}
      </Typography>
      {!isForbidden && onRetry && (
        <Button
          startIcon={<RefreshIcon />}
          onClick={onRetry}
          sx={{ mt: 2 }}
          variant="outlined"
        >
          Retry
        </Button>
      )}
    </Box>
  );
}