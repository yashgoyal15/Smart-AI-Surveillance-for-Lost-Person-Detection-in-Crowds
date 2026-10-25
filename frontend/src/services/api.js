// ------------------------------------------------------------------
// api.js
// One helper used by every service file, so the fetch() boilerplate
// (base URL, token, errors) is written only once.
// ------------------------------------------------------------------

export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
export const AI_URL = import.meta.env.VITE_AI_SERVICE_URL || "http://localhost:5001";

export function getToken() {
  return localStorage.getItem("lpds_token");
}

// photos and snapshots come back as "/uploads/..." -> turn into a full URL
export function fileUrl(path) {
  return path ? BASE_URL + path : null;
}

// if the token expired or is wrong, throw the user back to the login page
function forceLogout() {
  localStorage.removeItem("lpds_user");
  localStorage.removeItem("lpds_token");
  window.location.href = "/login";
}

async function sendRequest(path, options) {
  const token = getToken();
  const headers = { ...options.headers };

  // a JSON body needs this header, but a FormData (photo upload) must NOT have it,
  // the browser sets its own special header for files
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  } catch (err) {
    throw new Error("Cannot reach the server. Is the backend running?");
  }

  if (response.status === 401 && token && !path.startsWith("/api/auth/")) {
    forceLogout();
  }
  return response;
}

export async function apiRequest(path, options = {}) {
  const response = await sendRequest(path, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // the backend always sends { "error": "..." } when something fails
    throw new Error(data.error || "Something went wrong");
  }
  return data;
}

// downloads a file (used for the CSV audit log export)
export async function apiDownload(path, filename) {
  const response = await sendRequest(path, {});
  if (!response.ok) throw new Error("Download failed");

  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
