import { useEffect, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import { archiveConversation, listConversations } from "../../api/conversationApi";

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function ConversationHistoryDrawer({ open, activeConversationId, onClose, onLoad, onNew }) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError("");
    listConversations()
      .then((data) => setConversations(data.results || data))
      .catch(() => setError("Conversation history is unavailable right now."))
      .finally(() => setLoading(false));
  }, [open]);

  async function handleArchive(event, conversationId) {
    event.stopPropagation();
    try {
      await archiveConversation(conversationId);
      setConversations((current) => current.filter((item) => item.id !== conversationId));
      if (activeConversationId === conversationId) onNew();
    } catch {
      setError("Could not archive that conversation.");
    }
  }

  return (
    <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 400 } } }}>
      <Box sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
          <Typography variant="h6">Conversation history</Typography>
          <IconButton onClick={onClose} aria-label="Close conversation history"><CloseIcon /></IconButton>
        </Stack>
        <Button fullWidth variant="contained" startIcon={<AddIcon />} onClick={onNew} sx={{ mt: 2 }}>
          New conversation
        </Button>
      </Box>
      <Divider />
      {loading ? (
        <Box sx={{ display: "grid", placeItems: "center", py: 5 }}><CircularProgress size={24} /></Box>
      ) : error ? (
        <Typography color="error" variant="body2" sx={{ p: 2.5 }}>{error}</Typography>
      ) : conversations.length === 0 ? (
        <Typography color="text.secondary" variant="body2" sx={{ p: 2.5 }}>No saved conversations yet.</Typography>
      ) : (
        <List disablePadding>
          {conversations.map((conversation) => (
            <ListItemButton
              key={conversation.id}
              selected={conversation.id === activeConversationId}
              onClick={() => onLoad(conversation.id)}
              sx={{ alignItems: "flex-start", py: 1.75 }}
            >
              <ListItemText
                primary={conversation.title}
                secondary={formatDate(conversation.last_active_at)}
                primaryTypographyProps={{ noWrap: true, fontWeight: conversation.id === activeConversationId ? 700 : 500 }}
              />
              <Button size="small" color="inherit" onClick={(event) => handleArchive(event, conversation.id)}>Archive</Button>
            </ListItemButton>
          ))}
        </List>
      )}
    </Drawer>
  );
}
