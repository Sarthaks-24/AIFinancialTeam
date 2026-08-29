import api from "./api";

export const login = async (username, password) => {
  const response = await api.post("token/", { username, password });
  return response.data; // { access, refresh }
};