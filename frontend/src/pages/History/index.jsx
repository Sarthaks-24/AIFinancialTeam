import { useEffect, useState, useCallback } from "react";
import { Box, Typography, Paper, Stack, Chip } from "@mui/material";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";

import { CardSkeletons, EmptyState, ErrorState } from "../../components/Common/StateViews";
import { getHistory } from "../../api/historyApi";

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function History() {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getHistory();
      setHistory(res);
    } catch (err) {
      setError(err.response?.status || "network");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <Box>
      <Typography variant="h4" mb={3}>Query History</Typography>

      {loading && <CardSkeletons count={4} />}
      {!loading && error && <ErrorState status={error} onRetry={fetchHistory} />}

      {!loading && !error && (
        history.length === 0 ? (
          <EmptyState
            title="No questions asked yet"
            subtitle="Every question you ask the AI Financial Assistant will be logged here."
          />
        ) : (
          <Stack spacing={1.5}>
            {history.map((item, i) => (
              <Paper key={i} sx={{ p: { xs: 2, sm: 2.5 }, }}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", sm: "center" }}
                  spacing={0.5}
                  mb={1}
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    <QuestionAnswerOutlinedIcon fontSize="small" color="primary" />
                    <Chip size="small" label={item.agent} color="primary" variant="outlined" />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    {formatDate(item.created_at)}
                  </Typography>
                </Stack>
                <Typography fontWeight={600}>{item.question}</Typography>
              </Paper>
            ))}
          </Stack>
        )
      )}
    </Box>
  );
}