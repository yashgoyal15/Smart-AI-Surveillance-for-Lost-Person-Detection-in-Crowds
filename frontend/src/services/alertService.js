import { apiRequest, apiDownload } from "./api.js";

export function getAlerts(camId) {
  const query = camId ? `?cam=${camId}` : "";
  return apiRequest(`/api/alerts${query}`);
}

export function getDashboardStats() {
  return apiRequest("/api/dashboard/stats");
}

export function exportAuditLog() {
  return apiDownload("/api/alerts/export.csv", "audit_log.csv");
}
