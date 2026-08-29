import api from "./api";

export const getTasks = async ({ status, priority, search, page } = {}) => {
  const params = {};
  if (status) params.status = status;
  if (priority) params.priority = priority;
  if (search) params.search = search;
  if (page) params.page = page;

  const response = await api.get("tasks/", { params });
  return response.data; // { count, next, previous, results }
};

export const updateTaskStatus = async (task_id, status) => {
  const response = await api.post("tasks/update/", { task_id, status });
  return response.data;
};