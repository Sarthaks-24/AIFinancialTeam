import api from "./api";

export const runReconciliation = async () => {
  const response = await api.post("reconcile/");
  return response.data;
};

export const getReconciliationHistory = async (page = 1) => {
  const response = await api.get(`reconcile/history/?page=${page}`);
  return response.data;
};
