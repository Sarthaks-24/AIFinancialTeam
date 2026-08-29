import api from "./api";

export const askAgent = async (question, specialist) => {
  const response = await api.post("ask/", {
    question,
    ...(specialist ? { specialist } : {}),
  });

  return response.data;
};

export const askAgentVoice = async (audioBlob, options = {}) => {
  const form = new FormData();
  const filename = options.filename || "question.webm";
  form.append("audio", audioBlob, filename);
  if (options.specialist) {
    form.append("specialist", options.specialist);
  }
  if (options.voice_id) {
    form.append("voice_id", options.voice_id);
  }
  if (audioBlob.type) {
    form.append("mime_type", audioBlob.type);
  }

  const response = await api.post("voice/ask/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};

export const getSpecialists = async () => {
  const response = await api.get("specialists/");
  return response.data;
};

export const askAgentStream = async (question, specialist, onChunk, conversationId) => {
  const token = localStorage.getItem("access");
  const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/";
  
  const response = await fetch(`${baseUrl}ask/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      question,
      ...(specialist ? { specialist } : {}),
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    buffer += decoder.decode(value, { stream: true });
    
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    
    for (const part of parts) {
      if (part.startsWith("event: ")) {
        const lines = part.split("\n");
        const eventType = lines[0].replace("event: ", "").trim();
        const dataLine = lines.find(line => line.startsWith("data: "));
        if (dataLine) {
          const data = JSON.parse(dataLine.replace("data: ", ""));
          onChunk(eventType, data);
        }
      }
    }
  }
};
