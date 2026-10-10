import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const api = axios.create({ baseURL: `${BACKEND_URL}/api` });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("aegis_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function formatError(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg || JSON.stringify(d)).join(" ");
  return String(detail);
}

export const levelColor = (level) =>
  ({ safe: "#10B981", human: "#10B981", moderate: "#F59E0B", mixed: "#F59E0B", danger: "#EF4444", ai: "#EF4444" }[level] ||
  "#94A3B8");
