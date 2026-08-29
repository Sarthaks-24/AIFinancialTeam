import api from "./api";

export const runReconciliation = async (dataset_name = "canonical_60") => {
  const response = await api.post("reconcile/", { dataset_name });
  return response.data;
};

export const getReconciliationHistory = async (page = 1) => {
  const response = await api.get(`reconcile/history/?page=${page}`);
  return response.data;
};
