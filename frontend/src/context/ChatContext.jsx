import { createContext, useContext, useState, useEffect } from "react";
import { useAuth } from "./AuthContext";

const ChatContext = createContext(null);

const STORAGE_KEY_PREFIX = "ai_financial_team_chat_messages";
const CONVERSATION_KEY_PREFIX = "ai_financial_team_active_conversation";

export function ChatProvider({ children }) {
  const { user } = useAuth();
  const storageKey = `${STORAGE_KEY_PREFIX}:${user?.id || "anonymous"}`;
  const conversationKey = `${CONVERSATION_KEY_PREFIX}:${user?.id || "anonymous"}`;
  return <ChatSession key={storageKey} storageKey={storageKey} conversationKey={conversationKey}>{children}</ChatSession>;
}

function loadMessages(storageKey) {
  try {
    const saved = sessionStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function ChatSession({ children, storageKey, conversationKey }) {
  const [messages, setMessages] = useState(() => loadMessages(storageKey));
  const [activeConversationId, setActiveConversationId] = useState(() => {
    const saved = sessionStorage.getItem(conversationKey);
    return saved ? Number(saved) : null;
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify(messages));
    } catch {
      // sessionStorage full or unavailable — chat still works, just won't persist
    }
  }, [messages, storageKey]);

  useEffect(() => {
    if (activeConversationId) sessionStorage.setItem(conversationKey, String(activeConversationId));
    else sessionStorage.removeItem(conversationKey);
  }, [activeConversationId, conversationKey]);

  function addMessage(message) {
    setMessages((prev) => [...prev, message]);
  }

  function clearMessages() {
    setMessages([]);
    sessionStorage.removeItem(storageKey);
  }

  function startNewConversation() {
    setActiveConversationId(null);
    setMessages([]);
  }

  function loadConversation(conversation) {
    setActiveConversationId(conversation.id);
    setMessages((conversation.turns || []).map((turn) => (
      turn.role === "user"
        ? { id: `turn-${turn.id}`, role: "user", text: turn.content }
        : {
            id: `turn-${turn.id}`,
            role: "agent",
            result: { agent: turn.specialist_name, analysis: turn.content },
          }
    )));
  }

  return (
    <ChatContext.Provider value={{
      messages, addMessage, clearMessages, setMessages, activeConversationId,
      setActiveConversationId, startNewConversation, loadConversation,
    }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  return useContext(ChatContext);
}
