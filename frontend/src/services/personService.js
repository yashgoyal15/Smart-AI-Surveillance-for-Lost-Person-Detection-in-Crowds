import { apiRequest } from "./api.js";

export function getPersons() {
  return apiRequest("/api/persons");
}

// formData contains the text fields AND the photo file
export function addPerson(formData) {
  return apiRequest("/api/persons", { method: "POST", body: formData });
}

export function deletePerson(id) {
  return apiRequest(`/api/persons/${id}`, { method: "DELETE" });
}

// every place the person was seen, oldest first (cross-camera tracking)
export function getTrail(id) {
  return apiRequest(`/api/persons/${id}/trail`);
}
