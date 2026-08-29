import api from "./api";

export const getFinancialMonths = async () => {
  const response = await api.get("financial-data/months/");
  return response.data;
};

export const getFinancialData = async (month) => {
  const params = month ? { month } : {};
  const response = await api.get("financial-data/", { params });
  return response.data;
};

export const updateFinancialData = async (data) => {
  const response = await api.put("financial-data/", data);
  return response.data;
};