export const colors = {
  primary: "#000000",      // Black
  secondary: "#8B4513",    // Brown
  success: "#2E7D32",      
  warning: "#FFD700",      // Yellow
  error: "#D32F2F",
  background: "#FFFFFF",   // White
  paper: "#FFFFFF",        // White
  textPrimary: "#000000",  // Black
  textSecondary: "#8B4513",// Brown
};

// Extra tokens used by charts/status chips, kept separate so the
// core MUI palette above stays untouched.
export const chartColors = ["#000000", "#FFD700", "#8B4513", "#555555", "#DAA520", "#A0522D"];

export const statusColors = {
  Pending: { bg: "#FFF4E5", fg: "#8B4513" },
  "In Progress": { bg: "#FFF9C4", fg: "#000000" },
  Completed: { bg: "#E9F7EF", fg: "#1E7B34" },
  Blocked: { bg: "#FDEAEA", fg: "#B3261E" },
};

export const priorityColors = {
  Low: { bg: "#F5F5F5", fg: "#000000" },
  Medium: { bg: "#FFF9C4", fg: "#000000" },
  High: { bg: "#FDEAEA", fg: "#B3261E" },
};