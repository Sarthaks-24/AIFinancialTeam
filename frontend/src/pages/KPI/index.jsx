import { useEffect, useState, useCallback } from "react";
import { Box, Grid, Paper, Typography, Chip, Stack } from "@mui/material";
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
import { getKpis } from "../../api/kpiApi";
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

export default function KPI() {
  const [kpis, setKpis] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchKpis = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getKpis();
      setKpis(res);
    } catch (err) {
      setError(err.response?.status || "network");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKpis();
  }, [fetchKpis]);

  if (loading) {
    return (
      <Box>
        <Typography variant="h4" mb={3}>KPI Overview</Typography>
        <CardSkeletons count={3} />
      </Box>
    );
  }

  if (error) return <ErrorState status={error} onRetry={fetchKpis} />;

  const chartData = [
    { name: "Revenue", value: kpis.revenue },
    { name: "Expenses", value: kpis.expenses },
    { name: "EBITDA", value: kpis.ebitda },
  ];

  return (
    <Box>
      <Typography variant="h4" mb={3}>KPI Overview</Typography>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <KPICard title="Revenue" value={formatCurrency(kpis.revenue)} color={colors.success} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <KPICard title="Expenses" value={formatCurrency(kpis.expenses)} color={colors.error} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <KPICard title="EBITDA" value={formatCurrency(kpis.ebitda)} color={colors.primary} />
        </Grid>
      </Grid>

      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: { xs: 2, sm: 3 }, }}>
            <Typography variant="h6" mb={2}>Revenue vs Expenses vs EBITDA</Typography>
            <Box sx={{ width: "100%", height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
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
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: { xs: 2, sm: 3 }, height: "100%" }}>
            <Typography variant="h6" mb={2}>Cash &amp; Budget</Typography>
            <Stack spacing={2}>
              <Box>
                <Typography variant="caption" color="text.secondary">Cash Position</Typography>
                <Typography variant="h5" fontWeight={700}>{formatCurrency(kpis.cash_position)}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>Liquidity</Typography>
                <Chip label={kpis.liquidity_status} color={statusColor(kpis.liquidity_status)} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>Budget Status</Typography>
                <Chip label={kpis.budget_status} color={statusColor(kpis.budget_status)} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Budget Variance</Typography>
                <Typography variant="h6" fontWeight={700}>{formatCurrency(kpis.budget_variance)}</Typography>
              </Box>
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}