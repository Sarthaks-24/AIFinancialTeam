import { useEffect, useRef, useState } from "react";
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  CircularProgress,
  Chip,
  Stack,
  Avatar,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import MicIcon from "@mui/icons-material/Mic";
import StopCircleIcon from "@mui/icons-material/StopCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import SmartToyOutlinedIcon from "@mui/icons-material/SmartToyOutlined";
import PersonIcon from "@mui/icons-material/Person";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useChat } from "../../context/ChatContext";
import { askAgentStream, askAgentVoice, getSpecialists } from "../../api/chatApi";
import { chartColors } from "../../theme/colors";
import AgentOrb from "../../components/chat/AgentOrb";
import DelegationTimeline from "../../components/chat/DelegationTimeline";
import ExpertTeamPanel from "../../components/chat/ExpertTeamPanel";
import ConversationHistoryDrawer from "../../components/chat/ConversationHistoryDrawer";
import { createConversation, getConversation } from "../../api/conversationApi";

function playVoiceReply({ audio_base64, audio_mime, result, tts_fallback }, onPlay, onEnd) {
  if (audio_base64 && audio_mime) {
    const src = `data:${audio_mime};base64,${audio_base64}`;
    const audio = new Audio(src);
    if (onPlay) audio.onplay = onPlay;
    if (onEnd) audio.onended = onEnd;
    audio.play().catch(() => {
      speakWithBrowser(result?.analysis || "", onPlay, onEnd);
    });
    return;
  }

  if (tts_fallback) {
    speakWithBrowser(result?.analysis || "", onPlay, onEnd);
  } else if (onEnd) {
    onEnd();
  }
}

function speakWithBrowser(text, onPlay, onEnd) {
  if (!text || !window.speechSynthesis) {
    if (onEnd) onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text.replace(/[#*_`]/g, " ").slice(0, 800));
  utter.rate = 1;
  if (onPlay) utter.onstart = onPlay;
  if (onEnd) {
    utter.onend = onEnd;
    utter.onerror = onEnd;
  }
  window.speechSynthesis.speak(utter);
}

function formatCurrency(value) {
  return `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

const SERIES_LABELS = {
  revenue: "Revenue",
  expenses: "Expenses",
  ebitda: "EBITDA",
  cash_position: "Cash Position",
  budget: "Budget",
};

const SPECIALISTS = [
  { name: "Atlas", title: "Chief of Staff", description: "Strategic planning and executive decision support.", color: "#1976d2" },
  { name: "Vega", title: "Data Analyst", description: "Deep dives into metrics, trends, and data modeling.", color: "#9c27b0" },
  { name: "Nova", title: "Financial Advisor", description: "Budgeting, forecasting, and financial health.", color: "#2e7d32" },
  { name: "Aria", title: "Operations Manager", description: "Process optimization and daily workflow management.", color: "#ed6c02" },
  { name: "Orion", title: "Compliance Officer", description: "Regulatory adherence and risk management.", color: "#d32f2f" },
  { name: "Luna", title: "Product Specialist", description: "Product lifecycle and market analysis.", color: "#0288d1" },
];

function ChartBlock({ chart }) {
  if (!chart || !chart.data || chart.data.length === 0) return null;

  const isBar = chart.type === "bar";
  const ChartComponent = isBar ? BarChart : LineChart;

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        mb: 2,
        bgcolor: "background.paper",
      }}
    >
      {chart.title && (
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
          {chart.title}
        </Typography>
      )}

      <Box sx={{ width: "100%", height: 240 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ChartComponent data={chart.data} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey={chart.x_key || "month"} tick={{ fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              width={60}
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
            />
            <Tooltip formatter={(v) => formatCurrency(v)} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {chart.series.map((key, i) =>
              isBar ? (
                <Bar
                  key={key}
                  dataKey={key}
                  name={SERIES_LABELS[key] || key}
                  fill={chartColors[i % chartColors.length]}
                  radius={[4, 4, 0, 0]}
                />
              ) : (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={SERIES_LABELS[key] || key}
                  stroke={chartColors[i % chartColors.length]}
                  strokeWidth={2}
                  dot={{ r: 2 }}
                />
              )
            )}
          </ChartComponent>
        </ResponsiveContainer>
      </Box>
    </Paper>
  );
}

const DATA_PANEL_LABELS = {
  Atlas: "Key Metrics",
  Vega: "Key Metrics",
  Nova: "Financial Metrics",
  Aria: "Vendor Metrics",
  Orion: "Compliance Summary",
  Luna: "Details",
};

function AgentAnswer({ result, delegations = [], isComplete = false }) {
  if (!result) return null;

  const {
    agent,
    analysis,
    recommendation,
    ai_insight,
    ai_report,
    executive_summary,
    chart,
    charts,
    contributors,
    ...rest
  } = result;

  const panelLabel = DATA_PANEL_LABELS[agent] || "Details";
  const hasDelegationInfo = delegations.length > 0 || (Array.isArray(contributors) && contributors.length > 0);

  const extraEntries = Object.entries(rest).filter(
    ([key, value]) =>
      ![
        "agent",
        "analysis",
        "recommendation",
        "ai_insight",
        "ai_report",
        "executive_summary",
        "chart",
        "charts",
        "financial_data",
        "recommended_actions",
        "contributors",
        "execution",
        "conversation_id",
        "delegations",
      ].includes(key) &&
      typeof value !== "object"
  );

  const companionExperience = import.meta.env.VITE_COMPANION_EXPERIENCE === "true";
  const displayAgent = (companionExperience && agent === "Atlas") ? "Ava" : agent;

  return (
    <Box sx={{ width: "100%" }}>
      {displayAgent && (
        <Chip
          label={displayAgent}
          color="primary"
          size="small"
          sx={{
            mb: hasDelegationInfo ? 0.5 : 2,
            fontWeight: 600,
          }}
        />
      )}

      <DelegationTimeline
        delegations={delegations}
        contributors={contributors || []}
        isComplete={isComplete}
      />

      {analysis && (
        <Typography
          variant="body2"
          sx={{
            mb: 2,
            lineHeight: 1.8,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {analysis}
        </Typography>
      )}

      {ai_report && (
        <Typography
          variant="body2"
          sx={{
            mb: 2,
            lineHeight: 1.8,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {ai_report}
        </Typography>
      )}

      {/* Single chart (FP&A / Treasury / Budget agents) */}
      {chart && <ChartBlock chart={chart} />}

      {/* Multiple charts (Reporting agent) */}
      {Array.isArray(charts) && charts.map((c, i) => <ChartBlock key={i} chart={c} />)}

      {ai_insight && (
        <Paper
          sx={{
            bgcolor: "#f8fafc",
            p: 2,
            mb: 2,
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
          >
            {ai_insight}
          </Typography>
        </Paper>
      )}

      {executive_summary && (
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            mb: 2,
            bgcolor: "#fafafa",
          }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Executive Summary
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ whiteSpace: "pre-wrap" }}
          >
            {executive_summary}
          </Typography>
        </Paper>
      )}

      {Array.isArray(result.recommended_actions) && result.recommended_actions.length > 0 && (
        <Paper
          variant="outlined"
          sx={{ p: 2, mb: 2, bgcolor: "#fafafa" }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Recommended Actions
          </Typography>
          <Stack spacing={0.5}>
            {result.recommended_actions.map((action, i) => (
              <Typography key={i} variant="body2">• {action}</Typography>
            ))}
          </Stack>
        </Paper>
      )}

      {extraEntries.length > 0 && (
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            mb: 2,
            bgcolor: "#fafafa",
          }}
        >
          <Typography
            variant="subtitle2"
            sx={{
              mb: 1.5,
              fontWeight: 600,
            }}
          >
            {panelLabel}
          </Typography>

          <Stack spacing={1}>
            {extraEntries.map(([key, value]) => (
              <Box
                key={key}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 1,
                  borderBottom: "1px solid #eee",
                  pb: 1,
                }}
              >
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    textTransform: "capitalize",
                  }}
                >
                  {key.replace(/_/g, " ")}
                </Typography>

                <Typography
                  variant="body2"
                  fontWeight={600}
                >
                  {typeof value === "number"
                    ? (Number.isInteger(value) && value < 10000
                        ? value
                        : formatCurrency(value))
                    : String(value)}
                </Typography>
              </Box>
            ))}
          </Stack>
        </Paper>
      )}

      {recommendation && (
        <Paper
          sx={{
            bgcolor: "#E8F5E9",
            borderLeft: "5px solid green",
            p: 2,
          }}
        >
          <Typography
            variant="subtitle2"
            color="success.main"
            fontWeight={700}
            gutterBottom
          >
            Recommendation
          </Typography>

          <Typography variant="body2">
            {recommendation}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

export default function Chat() {
  const [question, setQuestion] = useState("");
  const [specialist, setSpecialist] = useState(null);
  const [specialists, setSpecialists] = useState(SPECIALISTS);
  const [expertsOpen, setExpertsOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isStreamingText, setIsStreamingText] = useState(false);
  const {
    messages, addMessage, clearMessages, setMessages, activeConversationId,
    setActiveConversationId, startNewConversation, loadConversation,
  } = useChat();
  const bottomRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const activeSpecialist = specialists.find((option) => option.name === specialist);
  const hasLeadingUserMessage = messages[0]?.role === "user";
  const companionExperience = import.meta.env.VITE_COMPANION_EXPERIENCE === "true";
  
  const presenceState = recording 
    ? "listening" 
    : (isPlayingAudio || isStreamingText) 
    ? "speaking" 
    : loading 
    ? "thinking" 
    : "idle";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    async function loadSpecialists() {
      try {
        const available = await getSpecialists();
        if (available.length > 0) {
          const merged = available.map((apiSpec) => {
            const localSpec = SPECIALISTS.find((s) => s.name === apiSpec.name);
            return { ...apiSpec, ...(localSpec || {}) };
          });
          setSpecialists(merged);
          setSpecialist((current) => (
            current && merged.some((option) => option.name === current) ? current : null
          ));
        }
      } catch {
        // Keep the local list as a resilient fallback while the API is unavailable.
      }
    }
    loadSpecialists();
  }, []);

  async function handleAsk() {
    const q = question.trim();
    if (!q || loading || recording) return;

    // Use a unique ID to find and update the streaming message
    const messageId = Date.now().toString();
    addMessage({ id: messageId, role: "user", text: q });
    setQuestion("");
    setLoading(true);
    
    // Add an empty agent message to stream into
    addMessage({ 
      id: messageId + "_reply", 
      role: "agent", 
      result: { analysis: "", agent: specialist || "Nexus" },
      delegations: [],
      isComplete: false,
    });

    let currentAnalysis = "";
    
    try {
      let conversationId = activeConversationId;
      if (!conversationId) {
        try {
          const conversation = await createConversation(q);
          conversationId = conversation.id;
          setActiveConversationId(conversationId);
        } catch {
        // Retain the existing session-storage chat when persistence is unavailable.
        }
      }

      await askAgentStream(q, specialist, (eventType, data) => {
        if (eventType === "metadata" && data.conversation_id && !conversationId) {
          conversationId = data.conversation_id;
          setActiveConversationId(data.conversation_id);
        }
        setMessages((prev) => 
          prev.map((msg) => {
            if (msg.id !== messageId + "_reply") return msg;

            if (eventType === "metadata") {
              return { ...msg, result: { ...data, analysis: currentAnalysis } };
            }
            if (eventType === "chunk") {
              setIsStreamingText(true);
              currentAnalysis += data.text;
              return { ...msg, result: { ...msg.result, analysis: currentAnalysis } };
            }
            if (eventType === "delegation_started") {
              return {
                ...msg,
                delegations: [...(msg.delegations || []), { from: data.from, to: data.to, activity: data.activity, status: "started" }],
              };
            }
            if (eventType === "delegation_completed") {
              return {
                ...msg,
                delegations: (msg.delegations || []).map((d) =>
                  d.from === data.from && d.to === data.to && d.status === "started"
                    ? { ...d, status: "completed" }
                    : d
                ),
              };
            }
            if (eventType === "delegation_failed") {
              return {
                ...msg,
                delegations: (msg.delegations || []).map((d) =>
                  d.from === data.from && d.to === data.to && d.status === "started"
                    ? { ...d, status: "failed", reason: data.reason }
                    : d
                ),
              };
            }
            if (eventType === "end") {
              setIsStreamingText(false);
              return { ...msg, isComplete: true };
            }
            return msg;
          })
        );
      }, conversationId);
    } catch {
      setIsStreamingText(false);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === messageId + "_reply"
            ? { ...msg, error: true, text: "I couldn't process that question. Please try again." }
            : msg
        )
      );
    } finally {
      setIsStreamingText(false);
      setLoading(false);
    }
  }

  async function handleVoiceBlob(blob) {
    setLoading(true);
    try {
      const data = await askAgentVoice(blob, { specialist });
      addMessage({
        role: "user",
        text: data.transcript || "(voice question)",
      });
      addMessage({ role: "agent", result: data.result });
      playVoiceReply(data, () => setIsPlayingAudio(true), () => setIsPlayingAudio(false));
    } catch (err) {
      const detail =
        err?.response?.data?.error ||
        "I couldn't process that voice question. Please try again.";
      addMessage({ role: "agent", error: true, text: detail });
    } finally {
      setLoading(false);
    }
  }

  async function toggleRecording() {
    if (loading) return;

    if (recording) {
      mediaRecorderRef.current?.stop();
      setRecording(false);
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      addMessage({
        role: "agent",
        error: true,
        text: "Voice recording is not supported in this browser.",
      });
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        await handleVoiceBlob(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      addMessage({
        role: "agent",
        error: true,
        text: "Microphone permission is required for voice questions.",
      });
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  }

  function handleAskDirectly(name) {
    setSpecialist(name);
    startNewConversation();
    setExpertsOpen(false);
  }

  async function handleLoadConversation(conversationId) {
    try {
      const conversation = await getConversation(conversationId);
      loadConversation(conversation);
      setHistoryOpen(false);
    } catch {
      addMessage({ role: "agent", error: true, text: "I couldn't load that conversation. Please try again." });
    }
  }

  function handleNewConversation() {
    startNewConversation();
    setHistoryOpen(false);
  }

  function handleAgentChange(event) {
    setSpecialist(event.target.value);
    startNewConversation();
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 112px)" }}>
      <Stack direction="row" justifyContent="flex-end" alignItems="center" spacing={1.5} mb={2} flexWrap="wrap" sx={{ gap: { xs: 2, sm: 1.5 } }}>
        {!companionExperience && (
          <Typography variant="h4" sx={{ mr: 'auto', fontSize: { xs: '1.5rem', sm: '2.125rem' } }}>AI Financial Workforce</Typography>
        )}
        <Stack direction="row" spacing={1} alignItems="center">
          {specialist && companionExperience && (
            <Button
              variant="outlined"
              startIcon={<SmartToyOutlinedIcon />}
              onClick={() => setExpertsOpen(true)}
              disabled={loading || recording}
            >
              Change agent
            </Button>
          )}
          {specialist && !companionExperience && (
            <FormControl size="small" sx={{ minWidth: 210 }}>
              <InputLabel id="specialist-label">Specialist</InputLabel>
              <Select
                labelId="specialist-label"
                label="Specialist"
                value={specialist}
                onChange={handleAgentChange}
                disabled={loading || recording}
              >
                {specialists.map((option) => (
                  <MenuItem key={option.name} value={option.name}>
                    {option.name} - {option.title}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {!companionExperience && activeConversationId && (
            <Button size="small" variant="text" onClick={handleNewConversation}>
              New chat
            </Button>
          )}
          {specialist && (
            <IconButton size="small" title="Conversation history" aria-label="Conversation history" onClick={() => setHistoryOpen(true)}>
              <HistoryOutlinedIcon fontSize="small" />
            </IconButton>
          )}
          {messages.length > 0 && (
            <IconButton size="small" onClick={clearMessages} title="Clear conversation" sx={{ color: "text.secondary" }}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          )}
        </Stack>
      </Stack>
      {companionExperience && (
        <ExpertTeamPanel
          open={expertsOpen}
          specialists={specialists}
          activeSpecialist={specialist}
          onClose={() => setExpertsOpen(false)}
          onAskDirectly={handleAskDirectly}
        />
      )}
      <ConversationHistoryDrawer
        open={historyOpen}
        activeConversationId={activeConversationId}
        onClose={() => setHistoryOpen(false)}
        onLoad={handleLoadConversation}
        onNew={handleNewConversation}
      />
      <Box
        sx={{
          flexGrow: 1,
          overflowY: "auto",
          pr: 0.5,
          mb: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          pb: 12, // Space for fixed command bar
        }}
      >
        {!specialist ? (
          <Box sx={{ mt: 8, width: '100%', maxWidth: 800, textAlign: 'center' }}>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              Who would you like to talk to?
            </Typography>
            <Typography variant="body1" color="text.secondary" mb={4}>
              Select an expert agent to start the conversation.
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={3} justifyContent="center">
              {specialists.map((s) => (
                <Paper
                  key={s.name}
                  onClick={() => {
                    startNewConversation();
                    setSpecialist(s.name);
                  }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      startNewConversation();
                      setSpecialist(s.name);
                    }
                  }}
                  sx={{
                    p: 3,
                    width: 240,
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s',
                    '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 12px 24px rgba(0,0,0,0.1)' }
                  }}
                >
                  <Box sx={{ width: 48, height: 48, borderRadius: '50%', bgcolor: s.color || '#1976d2', mx: 'auto', mb: 2, opacity: 0.8 }} />
                  <Typography variant="h6" fontWeight={600}>{s.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{s.title}</Typography>
                  <Typography variant="caption" color="text.secondary">{s.description}</Typography>
                </Paper>
              ))}
            </Stack>
          </Box>
        ) : (
          <>
            {messages.length === 0 && (
              <Stack
                direction={{ xs: "column", sm: "row" }}
                alignItems="center"
                spacing={{ xs: 2, sm: 3 }}
                sx={{ width: "100%", maxWidth: 720, mt: { xs: 5, sm: 7 }, px: 2 }}
              >
                <Box sx={{ flexShrink: 0 }}>
                  <AgentOrb state={presenceState} color={activeSpecialist?.color || "#1976d2"} />
                </Box>
                <Box sx={{ textAlign: { xs: "center", sm: "left" }, flex: 1, minWidth: 0 }}>
                {/* Developer mock toggle for returning user - purely for testing the UI states */}
                {window.location.search.includes('returning=true') ? (
                  <>
                    <Typography variant="h5" fontWeight={600} gutterBottom>
                      Welcome back.
                    </Typography>
                    <Typography variant="body1" color="text.secondary" mb={3}>
                      You were working on Q3 financial forecasts. Would you like to continue, explore it more deeply, or start something new?
                    </Typography>
                    <Stack direction="row" spacing={1} justifyContent={{ xs: "center", sm: "flex-start" }} flexWrap="wrap" useFlexGap>
                      <Button variant="contained" onClick={() => setQuestion("Let's continue with the Q3 forecasts.")}>Continue</Button>
                      <Button variant="outlined" onClick={() => setQuestion("I want to explore the Q3 forecasts more deeply.")}>Go deeper</Button>
                      <Button variant="text" onClick={() => setQuestion("Let's start something new.")}>Start new</Button>
                    </Stack>
                  </>
                ) : (
                  <>
                    <Typography variant="h5" fontWeight={600} gutterBottom>
                      Hi, I'm {activeSpecialist?.name}.
                    </Typography>
                    <Typography variant="body1" color="text.secondary" mb={3}>
                      I'm here to help with {activeSpecialist?.title?.toLowerCase()}. What would you like to work on?
                    </Typography>
                    {activeSpecialist?.suggested_prompts?.length > 0 && (
                      <Stack direction="row" justifyContent={{ xs: "center", sm: "flex-start" }} flexWrap="wrap" gap={1}>
                        {activeSpecialist.suggested_prompts.map((prompt) => (
                          <Chip key={prompt} label={prompt} onClick={() => setQuestion(prompt)} />
                        ))}
                      </Stack>
                    )}
                  </>
                )}
                </Box>
              </Stack>
            )}
          </>
        )}

        {specialist && (
        <Stack direction="row" alignItems="flex-start" spacing={{ xs: 1.5, sm: 3 }} sx={{ width: "100%", maxWidth: 960 }}>
          {specialist && messages.length > 0 && (
            <Box
              sx={{
                width: { xs: 76, sm: 120 },
                flexShrink: 0,
                position: "sticky",
                // Keep the orb below the fixed top navigation while the transcript scrolls.
                top: 92,
                zIndex: 2,
                alignSelf: "flex-start",
                // The first item is normally the user's prompt; align the agent presence with its reply.
                mt: hasLeadingUserMessage ? 12 : 0,
              }}
            >
              <AgentOrb state={presenceState} color={activeSpecialist?.color || "#1976d2"} size={72} />
            </Box>
          )}
          <Stack spacing={4} sx={{ width: "100%", minWidth: 0 }}>
          {messages.map((msg, i) => (
            <Box key={i} sx={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
              {msg.role === "user" ? (
                <Typography variant="h5" fontWeight={500} color="text.secondary" textAlign="center" sx={{ mb: 1, mt: 2, maxWidth: 600 }}>
                  {msg.text}
                </Typography>
              ) : (
                <Paper
                    sx={{
                      p: msg.error ? 2.25 : 4,
                      flex: 1,
                      minWidth: 0,
                    bgcolor: msg.error ? "rgba(211, 47, 47, 0.06)" : "background.paper",
                    border: msg.error ? "1px solid" : "none",
                    borderColor: msg.error ? "error.light" : "transparent",
                    boxShadow: msg.error ? "none" : "0 8px 32px rgba(0,0,0,0.06)",
                    borderRadius: 4,
                    overflow: "hidden",
                    wordBreak: "break-word",
                    boxSizing: "border-box",
                    }}
                  >
                    {msg.error ? (
                      <Typography variant="body2" color="error.main" textAlign="left" sx={{ lineHeight: 1.6 }}>
                        {msg.text}
                      </Typography>
                    ) : (
                      <AgentAnswer
                        result={msg.result}
                        delegations={msg.delegations || []}
                        isComplete={msg.isComplete !== false}
                      />
                    )}
                </Paper>
              )}
            </Box>
          ))}

          {loading && !companionExperience && (
            <Stack direction="row" spacing={1.5} alignItems="center" justifyContent="center">
              <CircularProgress size={24} />
            </Stack>
          )}
          </Stack>
        </Stack>
        )}

        <div ref={bottomRef} />
      </Box>

      {specialist && (
      <Paper
        sx={{
          p: 1,
          px: 2,
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          border: recording ? "1px solid #D32F2F" : "1px solid rgba(0,0,0,0.08)",
          borderRadius: 8,
          boxShadow: "0 8px 32px rgba(0,0,0,0.08)",
          position: "fixed",
          bottom: 24,
          left: "50%",
          transform: "translateX(-50%)",
          width: { xs: "90%", md: "60%", lg: 800 },
          bgcolor: "rgba(255, 255, 255, 0.9)",
          backdropFilter: "blur(12px)",
          zIndex: 10,
        }}
        elevation={0}
      >
        <IconButton
          color={recording ? "error" : "primary"}
          onClick={toggleRecording}
          disabled={loading}
          title={recording ? "Stop recording" : "Speak"}
          aria-label={recording ? "Stop recording" : "Speak"}
          sx={{ bgcolor: recording ? 'error.light' : 'primary.50', '&:hover': { bgcolor: recording ? 'error.main' : 'primary.100' } }}
        >
          {recording ? <StopCircleIcon /> : <MicIcon />}
        </IconButton>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder={
            recording ? "Listening… tap stop when done" : "Ask a financial question…"
          }
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          variant="standard"
          InputProps={{ disableUnderline: true, sx: { fontSize: '1.1rem' } }}
          disabled={recording}
          sx={{ py: 1 }}
        />
        <IconButton
          color="primary"
          onClick={handleAsk}
          disabled={loading || recording || !question.trim()}
          title="Send message"
          aria-label="Send message"
          sx={{
            bgcolor: (loading || recording || !question.trim()) ? 'transparent' : 'primary.main',
            color: (loading || recording || !question.trim()) ? 'inherit' : 'white',
            '&:hover': { bgcolor: 'primary.dark' },
            transition: 'all 0.2s'
          }}
        >
          <SendIcon fontSize="small" />
        </IconButton>
      </Paper>
      )}
    </Box>
  );
}
