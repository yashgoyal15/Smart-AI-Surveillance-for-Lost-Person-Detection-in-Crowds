import { apiRequest, apiDownload } from "./api.js";

// filters = { cam, status ("MATCH" | "POSSIBLE"), method, personId, limit } - all optional
export function getAlerts(filters = {}) {
  // old code called getAlerts("CAM-01"), so a plain string still works
  if (typeof filters === "string") filters = { cam: filters };
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiRequest(`/api/alerts${query}`);
}

export function getDashboardStats() {
  return apiRequest("/api/dashboard/stats");
}

export function exportAuditLog() {
  return apiDownload("/api/alerts/export.csv", "audit_log.csv");
}
