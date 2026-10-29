import { apiRequest } from "./api.js";

export function getPersons() {
  return apiRequest("/api/persons");
}

// formData contains the text fields AND one or more photos (field name "photos")
export function addPerson(formData) {
  return apiRequest("/api/persons", { method: "POST", body: formData });
}

// add more photos to a report that already exists (maximum 5 per person)
export function addPhotos(id, formData) {
  return apiRequest(`/api/persons/${id}/photos`, { method: "POST", body: formData });
}

// status can be "FOUND", "CLOSED" or "SEARCHING" (SEARCHING only to undo a MATCHED)
export function updateStatus(id, status, reason) {
  return apiRequest(`/api/persons/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, reason }),
  });
}

// closes the report and deletes the face data. The old alerts stay in the audit log.
export function deletePerson(id) {
  return apiRequest(`/api/persons/${id}`, { method: "DELETE" });
}

// every place the person was seen, oldest first (cross-camera tracking)
export function getTrail(id) {
  return apiRequest(`/api/persons/${id}/trail`);
}
