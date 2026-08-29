import { createTheme } from "@mui/material/styles";
import { colors } from "./colors";

const theme = createTheme({
  palette: {
    primary: { main: colors.primary },
    secondary: { main: colors.secondary },
    success: { main: colors.success },
    warning: { main: colors.warning },
    error: { main: colors.error },
    background: {
      default: colors.background,
      paper: colors.paper,
    },
    text: {
      primary: colors.textPrimary,
      secondary: colors.textSecondary,
    },
  },

  typography: {
    fontFamily: "Roboto, sans-serif",
    h4: { fontWeight: 700, fontSize: "1.75rem" },
    h5: { fontWeight: 600, fontSize: "1.3rem" },
    h6: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },

  shape: { borderRadius: 0 },

  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: "none",
          border: "1px solid #E5E9EF",
          backgroundImage: "none",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: "none",
          border: "1px solid #E5E9EF",
          backgroundImage: "none",
        },
        elevation1: {
          boxShadow: "none",
        },
        elevation2: {
          boxShadow: "none",
        },
        elevation3: {
          boxShadow: "none",
        },
        elevation4: {
          boxShadow: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { 
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          }
        },
        contained: {
          boxShadow: "none",
          "&:hover": {
            boxShadow: "none",
          }
        }
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#FFFFFF",
          boxShadow: "none",
          borderBottom: "1px solid #E5E9EF",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: "1px solid #E5E9EF",
          boxShadow: "none",
        },
      },
    },
  },

  breakpoints: {
    values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
  },
});

export default theme;