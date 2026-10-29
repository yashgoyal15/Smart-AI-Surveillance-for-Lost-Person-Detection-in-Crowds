import { apiRequest } from "./api.js";

export function getCameras() {
  return apiRequest("/api/cameras");
}

// tells the AI service to start reading this camera
export function startCamera(camId) {
  return apiRequest(`/api/cameras/${camId}/start`, { method: "POST" });
}

export function stopCamera(camId) {
  return apiRequest(`/api/cameras/${camId}/stop`, { method: "POST" });
}

// changes = { source, location, threshold (0.2-0.95 or null), calibPxPerCm (0.1-50 or null) }
export function updateCamera(camId, changes) {
  return apiRequest(`/api/cameras/${camId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

// add one more camera (the server stops you at its MAX_CAMERAS limit)
export function createCamera(location, source) {
  return apiRequest("/api/cameras", {
    method: "POST",
    body: JSON.stringify({ location, source }),
  });
}

// a camera can only be removed while it is stopped
export function deleteCamera(camId) {
  return apiRequest(`/api/cameras/${camId}`, { method: "DELETE" });
}
