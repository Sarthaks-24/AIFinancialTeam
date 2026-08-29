import api from "./api";

export async function createConversation(title = "") {
  const response = await api.post("conversations/", { title });
  return response.data;
}

export async function listConversations(page = 1) {
  const response = await api.get("conversations/", { params: { page } });
  return response.data;
}

export async function getConversation(conversationId) {
  const response = await api.get(`conversations/${conversationId}/`);
  return response.data;
}

export async function archiveConversation(conversationId) {
  const response = await api.post(`conversations/${conversationId}/archive/`);
  return response.data;
}
