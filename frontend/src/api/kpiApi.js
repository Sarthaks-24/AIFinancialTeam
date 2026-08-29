import api from "./api";

export const getKpis = async () => {
  const response = await api.get("kpis/");
  return response.data;
};