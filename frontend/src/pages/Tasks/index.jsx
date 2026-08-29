import { useEffect, useState, useCallback } from "react";
import {
  Box,
  Typography,
  Paper,
  Stack,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Chip,
  Pagination,
  InputAdornment,
  useMediaQuery,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import SearchIcon from "@mui/icons-material/Search";
import { toast } from "react-toastify";

import { CardSkeletons, EmptyState, ErrorState } from "../../components/Common/StateViews";
import { getTasks, updateTaskStatus } from "../../api/tasksApi";
import { statusColors, priorityColors } from "../../theme/colors";

const STATUS_OPTIONS = ["Pending", "In Progress", "Completed", "Blocked"];
const PRIORITY_OPTIONS = ["Low", "Medium", "High"];

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export default function Tasks() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const [tasks, setTasks] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  const PAGE_SIZE = 5;
  const pageCount = Math.max(1, Math.ceil(count / PAGE_SIZE));

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTasks({ status, priority, search, page });
      setTasks(res.results || []);
      setCount(res.count || 0);
    } catch (err) {
      setError(err.response?.status || "network");
    } finally {
      setLoading(false);
    }
  }, [status, priority, search, page]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(t);
  }, [searchInput]);

  async function handleStatusChange(task, newStatus) {
    setUpdatingId(task.id);
    const prevTasks = tasks;
    setTasks((cur) => cur.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)));

    try {
      await updateTaskStatus(task.id, newStatus);
      toast.success(`"${task.title}" marked as ${newStatus}`);
    } catch {
      setTasks(prevTasks);
      toast.error("Couldn't update task status. Try again.");
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <Box>
      <Typography variant="h4" mb={3}>Tasks</Typography>

      <Paper sx={{ p: { xs: 2, sm: 2.5 }, mb: 2.5 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField
            fullWidth
            size="small"
            placeholder="Search tasks..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 160 } }}>
            <InputLabel>Status</InputLabel>
            <Select
              label="Status"
              value={status}
              onChange={(e) => { setStatus(e.target.value); setPage(1); }}
            >
              <MenuItem value="">All statuses</MenuItem>
              {STATUS_OPTIONS.map((s) => (
                <MenuItem key={s} value={s}>{s}</MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 160 } }}>
            <InputLabel>Priority</InputLabel>
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => { setPriority(e.target.value); setPage(1); }}
            >
              <MenuItem value="">All priorities</MenuItem>
              {PRIORITY_OPTIONS.map((p) => (
                <MenuItem key={p} value={p}>{p}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {loading && <CardSkeletons count={5} />}
      {!loading && error && <ErrorState status={error} onRetry={fetchTasks} />}

      {!loading && !error && (
        tasks.length === 0 ? (
          <EmptyState
            title="No tasks match your filters"
            subtitle="Try clearing the search or filters above."
          />
        ) : (
          <>
            <Stack spacing={1.5}>
              {tasks.map((task) => {
                const sc = statusColors[task.status] || { bg: "#EEF2F6", fg: "#546679" };
                const pc = priorityColors[task.priority] || { bg: "#EEF2F6", fg: "#546679" };

                return (
                  <Paper key={task.id} sx={{ p: { xs: 2, sm: 2.5 }, }}>
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      justifyContent="space-between"
                      alignItems={{ xs: "flex-start", md: "center" }}
                      spacing={1.5}
                    >
                      <Box sx={{ minWidth: 0, flexGrow: 1 }}>
                        <Typography fontWeight={700}>{task.title}</Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {task.description}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                          Created {formatDate(task.created_at)}
                        </Typography>
                      </Box>

                      <Stack direction="row" spacing={1} alignItems="center" flexShrink={0}>
                        <Chip
                          size="small"
                          label={task.priority}
                          sx={{ bgcolor: pc.bg, color: pc.fg, fontWeight: 600 }}
                        />

                        <FormControl size="small" sx={{ minWidth: 140 }}>
                          <Select
                            value={task.status}
                            disabled={updatingId === task.id}
                            onChange={(e) => handleStatusChange(task, e.target.value)}
                            sx={{
                              bgcolor: sc.bg,
                              color: sc.fg,
                              fontWeight: 600,
                              "& .MuiOutlinedInput-notchedOutline": { border: "none" },
                            }}
                          >
                            {STATUS_OPTIONS.map((s) => (
                              <MenuItem key={s} value={s}>{s}</MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Stack>
                    </Stack>
                  </Paper>
                );
              })}
            </Stack>

            <Stack alignItems="center" mt={3}>
              <Pagination
                count={pageCount}
                page={page}
                onChange={(_, val) => setPage(val)}
                color="primary"
                size={isMobile ? "small" : "medium"}
              />
            </Stack>
          </>
        )
      )}
    </Box>
  );
}
