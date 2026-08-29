import { useState, useEffect } from "react";
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Stack,
  CircularProgress,
  Alert,
  Divider,
  Pagination,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlined";
import SpeedIcon from "@mui/icons-material/Speed";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import InsightsIcon from "@mui/icons-material/Insights";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import KPICard from "../../components/dashboard/KPICard";
import { colors } from "../../theme/colors";
import { runReconciliation, getReconciliationHistory } from "../../api/reconciliationApi";

const EXCEPTION_COLORS = {
  amount_mismatch: "#D32F2F",
  date_mismatch: "#F57C00",
  missing_in_ledger: "#7B1FA2",
  missing_in_settlement: "#1565C0",
  unresolvable: "#616161",
};

const PIE_COLORS = ["#2E7D32", "#D32F2F", "#F57C00", "#7B1FA2", "#1565C0", "#616161"];

function formatCurrency(value) {
  if (value == null) return "—";
  const n = Number(value || 0);
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export default function Reconciliation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [page, setPage] = useState(1);

  const fetchHistory = async (p = 1) => {
    setHistoryLoading(true);
    try {
      const res = await getReconciliationHistory(p);
      setHistory(res);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(page);
  }, [page]);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await runReconciliation();
      setData(result);
      fetchHistory(1); // Refresh history after run
      setPage(1);
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Failed to run reconciliation. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  };

  const pieData = data
    ? (() => {
        const exceptionTypes = {};
        (data.exceptions || []).forEach((e) => {
          exceptionTypes[e.type] = (exceptionTypes[e.type] || 0) + 1;
        });
        const slices = [
          { name: "Matched", value: data.matched },
          ...Object.entries(exceptionTypes).map(([key, val]) => ({
            name: key.replace(/_/g, " "),
            value: val,
          })),
        ];
        return slices;
      })()
    : [];

  return (
    <Box>
      {/* Header */}
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={2}
        mb={3}
      >
        <Box>
          <Typography variant="h4">Reconciliation Engine</Typography>
          <Typography variant="body2" color="text.secondary" mt={0.5}>
            Match Razorpay settlements against internal ledger records using AI
          </Typography>
        </Box>
        <Button
          variant="contained"
          size="large"
          startIcon={
            loading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <PlayArrowIcon />
            )
          }
          onClick={handleRun}
          disabled={loading}
          sx={{
            px: 4,
            py: 1.5,
            fontWeight: 700,
            textTransform: "none",
            fontSize: 16,
          }}
        >
          {loading ? "Running…" : "Run Reconciliation"}
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Paper sx={{ p: 6, textAlign: "center" }}>
          <CircularProgress size={48} />
          <Typography variant="h6" mt={2} color="text.secondary">
            Running AI reconciliation engine…
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={1}>
            Matching records and classifying discrepancies
          </Typography>
        </Paper>
      )}

      {data && !loading && (
        <>
          {/* Track 04 Buildathon Alert if Unresolved Exceptions Exist */}
          {(data.accuracy?.unresolved?.length > 0) && (
            <Alert severity="warning" sx={{ mb: 3 }} icon={<InsightsIcon />}>
              <Typography variant="subtitle2">
                Honest Exception List: {data.accuracy.unresolved.length} unresolvable item(s) found.
              </Typography>
              <Typography variant="body2">
                These records fell below the AI confidence threshold (0.5) or lacked sufficient context. System flags them for manual review instead of forcing an incorrect match.
              </Typography>
            </Alert>
          )}

          {/* KPI Cards */}
          <Grid container spacing={2.5} mb={2.5}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <KPICard
                title="Total Processed"
                value={data.total_processed}
                color={colors.primary}
                icon={<ReceiptLongIcon fontSize="large" />}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <KPICard
                title="Matched"
                value={data.matched}
                color={colors.success}
                icon={
                  <CheckCircleIcon fontSize="large" sx={{ color: colors.success }} />
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <KPICard
                title="Match Rate"
                value={`${data.match_rate_pct}%`}
                color={data.match_rate_pct >= 90 ? colors.success : colors.error}
                icon={
                  <SpeedIcon
                    fontSize="large"
                    sx={{
                      color:
                        data.match_rate_pct >= 90 ? colors.success : colors.error,
                    }}
                  />
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <KPICard
                title="Exceptions"
                value={data.exceptions_count}
                color={colors.error}
                icon={
                  <ErrorOutlineIcon
                    fontSize="large"
                    sx={{ color: colors.error }}
                  />
                }
              />
            </Grid>
          </Grid>

          {/* AI Accuracy Metrics Cards */}
          {data.accuracy?.overall && (
            <Grid container spacing={2.5} mb={2.5}>
              <Grid size={{ xs: 12, sm: 3 }}>
                <Paper sx={{ p: 2, textAlign: "center", borderTop: `4px solid ${colors.secondary}` }}>
                  <Typography variant="caption" color="text.secondary">AI Precision</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {Math.round(data.accuracy.overall.precision * 100)}%
                  </Typography>
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <Paper sx={{ p: 2, textAlign: "center", borderTop: `4px solid ${colors.secondary}` }}>
                  <Typography variant="caption" color="text.secondary">AI Recall</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {Math.round(data.accuracy.overall.recall * 100)}%
                  </Typography>
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <Paper sx={{ p: 2, textAlign: "center", borderTop: `4px solid ${colors.secondary}` }}>
                  <Typography variant="caption" color="text.secondary">AI F1 Score</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {data.accuracy.overall.f1.toFixed(2)}
                  </Typography>
                </Paper>
              </Grid>
              <Grid size={{ xs: 12, sm: 3 }}>
                <Paper sx={{ p: 2, textAlign: "center", borderTop: `4px solid ${colors.secondary}` }}>
                  <Typography variant="caption" color="text.secondary">Throughput</Typography>
                  <Typography variant="h5" fontWeight={700}>
                    {data.throughput_records_per_sec || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">records / sec</Typography>
                </Paper>
              </Grid>
            </Grid>
          )}

          {/* Chart + AI Summary Row */}
          <Grid container spacing={2.5} mb={2.5}>
            <Grid size={{ xs: 12, md: 5 }}>
              <Paper sx={{ p: 3, height: "100%" }}>
                <Typography variant="h6" mb={2}>
                  Reconciliation Breakdown
                </Typography>
                <Box sx={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={3}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {pieData.map((_, i) => (
                          <Cell
                            key={i}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
                <Stack direction="row" spacing={2} mt={1} justifyContent="center">
                  <Typography variant="caption" color="text.secondary">
                    ⏱ Processing time: {data.processing_time_ms}ms
                  </Typography>
                </Stack>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, md: 7 }}>
              <Paper sx={{ p: 3, height: "100%" }}>
                <Typography variant="h6" mb={2}>
                  AI Executive Summary
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ whiteSpace: "pre-line", lineHeight: 1.8 }}
                >
                  {data.ai_summary}
                </Typography>

                <Stack direction="row" spacing={2} mt={3} flexWrap="wrap" useFlexGap>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Settlement records
                    </Typography>
                    <Typography fontWeight={700}>
                      {data.total_settlement_records}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Ledger records
                    </Typography>
                    <Typography fontWeight={700}>
                      {data.total_ledger_records}
                    </Typography>
                  </Box>
                </Stack>
              </Paper>
            </Grid>
          </Grid>

          {/* Exception Table */}
          {data.exceptions?.length > 0 && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" mb={2}>
                Exception List ({data.exceptions.length})
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 700 }}>Txn ID</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Type</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>Confidence</TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align="right">
                        Settlement Amt
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align="right">
                        Ledger Amt
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }} align="right">
                        Delta
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>AI Reasoning</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.exceptions.map((exc, i) => (
                      <TableRow key={i} hover>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600} fontFamily="monospace">
                            {exc.txn_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={exc.type?.replace(/_/g, " ")}
                            size="small"
                            sx={{
                              fontWeight: 600,
                              bgcolor:
                                (EXCEPTION_COLORS[exc.type] || "#616161") + "18",
                              color: EXCEPTION_COLORS[exc.type] || "#616161",
                              textTransform: "capitalize",
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          {exc.confidence != null ? (
                            <Chip 
                               size="small" 
                               label={`${Math.round(exc.confidence * 100)}%`} 
                               color={exc.confidence >= 0.8 ? "success" : exc.confidence >= 0.5 ? "warning" : "error"}
                               variant="outlined"
                            />
                          ) : (
                            <Typography variant="caption" color="text.secondary">N/A</Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(exc.settlement_amount)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(exc.ledger_amount)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            color={exc.delta ? "error" : "text.secondary"}
                          >
                            {exc.delta != null ? formatCurrency(Math.abs(exc.delta)) : "—"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 320 }}>
                            {exc.ai_reasoning}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}
        </>
      )}

      {/* Empty state */}
      {!data && !loading && !error && (
        <Paper sx={{ p: 6, textAlign: "center" }}>
          <ReceiptLongIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            Ready to reconcile
          </Typography>
          <Typography variant="body2" color="text.disabled" mt={1}>
            Click "Run Reconciliation" to match Razorpay settlements against your
            internal ledger using AI analysis.
          </Typography>
        </Paper>
      )}
      
      {/* Run History Section */}
      <Box mt={6} mb={4}>
        <Typography variant="h6" mb={2}>Reconciliation History</Typography>
        <Paper sx={{ p: 2 }}>
            {historyLoading ? (
               <Box textAlign="center" p={3}><CircularProgress size={30} /></Box>
            ) : history && history.results.length > 0 ? (
               <>
                 <TableContainer>
                   <Table size="small">
                     <TableHead>
                       <TableRow>
                         <TableCell>Date</TableCell>
                         <TableCell>Total</TableCell>
                         <TableCell>Exceptions</TableCell>
                         <TableCell>Match Rate</TableCell>
                         <TableCell>F1 Score</TableCell>
                       </TableRow>
                     </TableHead>
                     <TableBody>
                        {history.results.map((hRun) => (
                           <TableRow key={hRun.id}>
                              <TableCell>{new Date(hRun.created_at).toLocaleString()}</TableCell>
                              <TableCell>{hRun.total_processed}</TableCell>
                              <TableCell>{hRun.exceptions_count}</TableCell>
                              <TableCell>
                                <Chip size="small" label={`${hRun.match_rate_pct}%`} color={hRun.match_rate_pct > 90 ? "success" : "default"} />
                              </TableCell>
                              <TableCell>
                                {hRun.accuracy_overall_f1 != null ? hRun.accuracy_overall_f1.toFixed(2) : "—"}
                              </TableCell>
                           </TableRow>
                        ))}
                     </TableBody>
                   </Table>
                 </TableContainer>
                 {history.count > 10 && (
                   <Box display="flex" justifyContent="center" mt={2}>
                     <Pagination 
                        count={Math.ceil(history.count / 10)} 
                        page={page} 
                        onChange={(_, val) => setPage(val)} 
                        color="primary"
                     />
                   </Box>
                 )}
               </>
            ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center" p={3}>
                   No past reconciliation runs found.
                </Typography>
            )}
        </Paper>
      </Box>

    </Box>
  );
}
