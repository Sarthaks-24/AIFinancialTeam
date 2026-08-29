import { useEffect, useState, useCallback } from "react";
import {
  Grid,
  Box,
  Paper,
  Typography,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
} from "@mui/material";
import FavoriteIcon from "@mui/icons-material/Favorite";
import CurrencyRupeeIcon from "@mui/icons-material/CurrencyRupee";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import AssignmentIcon from "@mui/icons-material/Assignment";
import LightbulbOutlinedIcon from "@mui/icons-material/LightbulbOutlined";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import KPICard from "../../components/dashboard/KPICard";
import { CardSkeletons, ErrorState } from "../../components/Common/StateViews";
import { getDashboard } from "../../api/dashboardApi";
import { colors, chartColors } from "../../theme/colors";

function formatCurrency(value) {
  const n = Number(value || 0);
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

const statusColor = (status) => {
  if (!status) return "default";
  const s = status.toLowerCase();
  if (s.includes("healthy") || s.includes("good")) return "success";
  if (s.includes("moderate")) return "warning";
  if (s.includes("high") || s.includes("risk") || s.includes("overspend")) return "error";
  return "default";
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDashboard();
      setDashboard(res);
    } catch (err) {
      setError(err.response?.status || "network");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" mb={3}>Dashboard</Typography>
        <CardSkeletons count={4} />
      </Box>
    );
  }

  if (error) {
    return <ErrorState status={error} onRetry={fetchDashboard} />;
  }

  const chartData = [
    { name: "Revenue", value: dashboard.revenue },
    { name: "EBITDA", value: dashboard.ebitda },
    { name: "Cash", value: dashboard.cash_position },
  ];

  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={1}
        mb={3}
      >
        <Typography variant="h4">Dashboard</Typography>
        <Chip
          label={dashboard.financial_status}
          color={statusColor(dashboard.financial_status)}
          sx={{ fontWeight: 700 }}
        />
      </Stack>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Health Score"
            value={dashboard.health_score}
            color={colors.error}
            icon={<FavoriteIcon fontSize="large" color="error" />}
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Revenue"
            value={formatCurrency(dashboard.revenue)}
            color={colors.success}
            icon={<CurrencyRupeeIcon fontSize="large" color="success" />}
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Cash Position"
            value={formatCurrency(dashboard.cash_position)}
            color={colors.primary}
            icon={<AccountBalanceWalletIcon fontSize="large" color="primary" />}
          />
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <KPICard
            title="Pending Tasks"
            value={dashboard.pending_tasks}
            color={colors.warning}
            icon={<AssignmentIcon fontSize="large" color="warning" />}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: { xs: 2, sm: 3 }, height: "100%" }}>
            <Typography variant="h6" mb={2}>Financial Snapshot</Typography>
            <Box sx={{ width: "100%", height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ left: 0, right: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} width={70} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => formatCurrency(v)} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={chartColors[i % chartColors.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>

            <Stack direction="row" spacing={3} mt={2} flexWrap="wrap" useFlexGap>
              <Box>
                <Typography variant="caption" color="text.secondary">Budget status</Typography>
                <br />
                <Chip size="small" label={dashboard.budget_status} color={statusColor(dashboard.budget_status)} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Budget variance</Typography>
                <Typography fontWeight={700}>{formatCurrency(dashboard.budget_variance)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Liquidity</Typography>
                <br />
                <Chip size="small" label={dashboard.liquidity_status} color={statusColor(dashboard.liquidity_status)} />
              </Box>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: { xs: 2, sm: 3 }, height: "100%" }}>
            <Typography variant="h6" mb={1.5}>Recommendations</Typography>
            {dashboard.recommendations?.length ? (
              <List dense>
                {dashboard.recommendations.map((rec, i) => (
                  <ListItem key={i} disableGutters alignItems="flex-start">
                    <ListItemIcon sx={{ minWidth: 32, mt: 0.5 }}>
                      <LightbulbOutlinedIcon fontSize="small" color="warning" />
                    </ListItemIcon>
                    <ListItemText primary={rec} />
                  </ListItem>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary">No recommendations right now.</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mt: 2.5 }}>
        <Typography variant="h6" mb={1}>Executive Summary</Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "pre-line", lineHeight: 1.8 }}
        >
          {dashboard.executive_summary}
        </Typography>
      </Paper>
    </Box>
  );
}