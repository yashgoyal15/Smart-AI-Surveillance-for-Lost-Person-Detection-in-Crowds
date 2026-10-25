import React, { useState } from "react";
import { Upload } from "lucide-react";
import { addPerson } from "../../services/personService.js";

const inputClass =
  "w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function RegisterPersonView({ onPersonAdded }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("Male");
  const [lastSeen, setLastSeen] = useState("");
  const [contact, setContact] = useState("");
  const [photo, setPhoto] = useState(null);          // the chosen File
  const [photoPreview, setPhotoPreview] = useState(""); // temporary URL to show it
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handlePhotoChange(e) {
    const file = e.target.files[0];
    if (!file) return;

    // check on the frontend first so the user gets an instant message
    if (!file.type.startsWith("image/")) {
      setErrorMsg("Please choose an image file (jpg, png or webp).");
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setErrorMsg("The photo is too big. Maximum size is 8 MB.");
      return;
    }

    setErrorMsg("");
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (!photo) {
      setErrorMsg("Please upload a clear, front-facing photo.");
      return;
    }

    // FormData is how a form with a file is sent to the server
    const formData = new FormData();
    formData.append("name", name);
    formData.append("age", age);
    formData.append("gender", gender);
    formData.append("lastSeen", lastSeen);
    formData.append("contact", contact);
    formData.append("photo", photo);

    setSubmitting(true);
    try {
      // the backend saves the photo, the AI service reads the face from it,
      // and the face vector is stored in PostgreSQL
      await addPerson(formData);

      setSuccessMsg("Report submitted. The cameras will now look for this person.");
      setName("");
      setAge("");
      setGender("Male");
      setLastSeen("");
      setContact("");
      setPhoto(null);
      setPhotoPreview("");
      if (onPersonAdded) onPersonAdded();
    } catch (err) {
      setErrorMsg(err.message); // e.g. "No clear face found in this photo..."
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md">
      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-lg p-5 space-y-4">
        <div>
          <label className="text-xs text-slate-400">Full name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} required />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-slate-400">Age</label>
            <input
              value={age}
              onChange={(e) => setAge(e.target.value)}
              type="number"
              min="0"
              max="120"
              className={inputClass}
              required
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Gender</label>
            <select value={gender} onChange={(e) => setGender(e.target.value)} className={inputClass}>
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400">Last seen location</label>
          <input
            value={lastSeen}
            onChange={(e) => setLastSeen(e.target.value)}
            className={inputClass}
            placeholder="e.g. Platform 2"
            required
          />
        </div>

        <div>
          <label className="text-xs text-slate-400">Your contact number</label>
          <input value={contact} onChange={(e) => setContact(e.target.value)} className={inputClass} required />
        </div>

        <div>
          <label className="text-xs text-slate-400">Reference photo (clear, front-facing, good light)</label>
          <label className="mt-1 flex flex-col items-center gap-2 border border-dashed border-slate-700 hover:border-emerald-500 rounded px-3 py-4 text-sm text-slate-400 cursor-pointer">
            {photoPreview ? (
              <img src={photoPreview} alt="preview" className="h-32 rounded object-cover" />
            ) : (
              <Upload size={18} />
            )}
            {photo ? photo.name : "Click to choose a photo"}
            <input type="file" accept="image/*" onChange={handlePhotoChange} className="hidden" />
          </label>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-slate-950 font-semibold text-sm rounded py-2 transition-colors"
        >
          {submitting ? "Reading the face..." : "Submit report"}
        </button>

        {successMsg && <p className="text-emerald-400 text-xs text-center">{successMsg}</p>}
        {errorMsg && <p className="text-red-400 text-xs text-center">{errorMsg}</p>}
      </form>
    </div>
  );
}
