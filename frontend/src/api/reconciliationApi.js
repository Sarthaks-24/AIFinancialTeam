import api from "./api";

export const runReconciliation = async () => {
  const response = await api.post("reconcile/");
  return response.data;
};
