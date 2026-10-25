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

// change where the camera reads from (webcam number, video file, phone URL, RTSP)
export function updateCamera(camId, changes) {
  return apiRequest(`/api/cameras/${camId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}
