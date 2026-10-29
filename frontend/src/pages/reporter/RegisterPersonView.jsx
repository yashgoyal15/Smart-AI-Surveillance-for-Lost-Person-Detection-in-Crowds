import React, { useState } from "react";
import { Upload, X } from "lucide-react";
import { addPerson } from "../../services/personService.js";
import { COLOR_NAMES } from "../../utils/colors.js";

const inputClass =
  "w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm outline-none focus:border-emerald-500";
const MAX_PHOTOS = 5;

export default function RegisterPersonView({ onPersonAdded }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("Male");
  const [lastSeen, setLastSeen] = useState("");
  const [contact, setContact] = useState("");
  // what the person was wearing - the cameras use this when the face is hidden
  const [upperColor, setUpperColor] = useState("");
  const [lowerColor, setLowerColor] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [notes, setNotes] = useState("");
  const [photos, setPhotos] = useState([]);          // list of { file, preview }
  const [report, setReport] = useState([]);          // quality result of every photo, from the server
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handlePhotoChange(e) {
    const chosen = Array.from(e.target.files);
    e.target.value = ""; // so the same file can be chosen again later
    setErrorMsg("");

    const next = [...photos];
    for (const file of chosen) {
      if (!file.type.startsWith("image/")) {
        setErrorMsg("Please choose image files only (jpg, png or webp).");
        continue;
      }
      if (file.size > 8 * 1024 * 1024) {
        setErrorMsg(`${file.name} is too big. Maximum size is 8 MB.`);
        continue;
      }
      if (next.length >= MAX_PHOTOS) {
        setErrorMsg(`You can add up to ${MAX_PHOTOS} photos.`);
        break;
      }
      next.push({ file, preview: URL.createObjectURL(file) });
    }
    setPhotos(next);
  }

  function removePhoto(index) {
    setPhotos(photos.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");
    setReport([]);

    if (photos.length === 0) {
      setErrorMsg("Please upload at least one clear, front-facing photo.");
      return;
    }

    // FormData is how a form with files is sent to the server
    const formData = new FormData();
    formData.append("name", name);
    formData.append("age", age);
    formData.append("gender", gender);
    formData.append("lastSeen", lastSeen);
    formData.append("contact", contact);
    if (upperColor) formData.append("upperColor", upperColor);
    if (lowerColor) formData.append("lowerColor", lowerColor);
    if (heightCm) formData.append("heightCm", heightCm);
    if (notes) formData.append("notes", notes);
    photos.forEach((p) => formData.append("photos", p.file));

    setSubmitting(true);
    try {
      // the server checks the quality of every photo; only the good ones are used
      const saved = await addPerson(formData);
      setReport(saved.photoReport || []);

      const used = (saved.photoReport || []).filter((r) => r.accepted).length;
      setSuccessMsg(`Report submitted using ${used} photo(s). The cameras will now look for this person.`);
      setName("");
      setAge("");
      setGender("Male");
      setLastSeen("");
      setContact("");
      setUpperColor("");
      setLowerColor("");
      setHeightCm("");
      setNotes("");
      setPhotos([]);
      if (onPersonAdded) onPersonAdded();
    } catch (err) {
      setErrorMsg(err.message); // e.g. "No clear face found in any photo..."
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
            <input value={age} onChange={(e) => setAge(e.target.value)} type="number" min="0" max="120" className={inputClass} required />
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
          <input value={lastSeen} onChange={(e) => setLastSeen(e.target.value)} className={inputClass} placeholder="e.g. Platform 2" required />
        </div>

        <div>
          <label className="text-xs text-slate-400">Your contact number</label>
          <input value={contact} onChange={(e) => setContact(e.target.value)} className={inputClass} required />
        </div>

        {/* clothes and body details: help the cameras when the face is turned away or covered */}
        <div className="border border-slate-800 rounded p-3 space-y-3">
          <p className="text-xs text-slate-400">What were they wearing? (optional, but helps when the face is not visible)</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400">Top / shirt colour</label>
              <select value={upperColor} onChange={(e) => setUpperColor(e.target.value)} className={inputClass}>
                <option value="">Not sure</option>
                {COLOR_NAMES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Trousers / skirt colour</label>
              <select value={lowerColor} onChange={(e) => setLowerColor(e.target.value)} className={inputClass}>
                <option value="">Not sure</option>
                {COLOR_NAMES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Height in cm</label>
            <input value={heightCm} onChange={(e) => setHeightCm(e.target.value)} type="number" min="40" max="230" className={inputClass} />
          </div>
          <div>
            <label className="text-xs text-slate-400">Other details (bag, glasses, cap ...)</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} className={inputClass} maxLength={200} />
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400">
            Photos ({photos.length}/{MAX_PHOTOS}) - clear, front-facing, good light. More photos from different angles help.
          </label>
          <div className="mt-1 flex flex-wrap gap-2">
            {photos.map((p, i) => (
              <div key={i} className="relative">
                <img src={p.preview} alt="preview" className="h-20 w-20 rounded object-cover" />
                <button type="button" onClick={() => removePhoto(i)} className="absolute -top-1 -right-1 bg-slate-950 rounded-full p-0.5 text-slate-300 hover:text-red-400">
                  <X size={14} />
                </button>
              </div>
            ))}
            {photos.length < MAX_PHOTOS && (
              <label className="h-20 w-20 flex flex-col items-center justify-center gap-1 border border-dashed border-slate-700 hover:border-emerald-500 rounded text-xs text-slate-400 cursor-pointer">
                <Upload size={16} />
                Add
                <input type="file" accept="image/*" multiple onChange={handlePhotoChange} className="hidden" />
              </label>
            )}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-slate-950 font-semibold text-sm rounded py-2 transition-colors"
        >
          {submitting ? "Checking the photos..." : "Submit report"}
        </button>

        {successMsg && <p className="text-emerald-400 text-xs text-center">{successMsg}</p>}
        {errorMsg && <p className="text-red-400 text-xs text-center">{errorMsg}</p>}

        {/* quality result of each photo */}
        {report.length > 0 && (
          <ul className="text-xs space-y-1">
            {report.map((r, i) => (
              <li key={i} className={r.accepted ? "text-slate-300" : "text-amber-400"}>
                {r.accepted ? "Used" : "Skipped"}: {r.name}
                {r.quality !== undefined && ` (quality ${Math.round(r.quality * 100)}%)`}
                {r.reason && ` - ${r.reason}`}
              </li>
            ))}
          </ul>
        )}
      </form>
    </div>
  );
}
