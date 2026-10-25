import { apiRequest } from "./api.js";

// returns { token, user: { id, name, email, role } }
export function loginUser(role, email, password) {
  return apiRequest("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ role, email, password }),
  });
}

// operatorCode is only needed when role is "operator"
export function registerUser(role, name, email, password, operatorCode) {
  return apiRequest("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ role, name, email, password, operatorCode }),
  });
}
