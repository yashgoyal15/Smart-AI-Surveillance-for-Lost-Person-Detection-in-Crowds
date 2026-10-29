import React, { useEffect, useState } from "react";
import { Trash2, ImagePlus, CheckCircle2 } from "lucide-react";
import { getPersons, deletePerson, updateStatus, addPhotos } from "../../services/personService.js";
import { fileUrl } from "../../services/api.js";
import { formatTime } from "../../utils/format.js";

// the text and colour shown for each status of a report
const STATUS_LOOK = {
  SEARCHING: { text: "Still searching", css: "bg-amber-500/10 text-amber-400" },
  MATCHED: { text: "Spotted", css: "bg-emerald-500/10 text-emerald-400" },
  FOUND: { text: "Found", css: "bg-sky-500/10 text-sky-400" },
  CLOSED: { text: "Closed", css: "bg-slate-700/40 text-slate-400" },
};

export default function MyReportsView({ refreshKey, onChange }) {
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [infoMsg, setInfoMsg] = useState("");

  // load again whenever refreshKey changes (after a new report or a change)
  useEffect(() => {
    getPersons()
      .then(setPersons)
      .catch((err) => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  async function run(action) {
    setErrorMsg("");
    setInfoMsg("");
    try {
      await action();
      if (onChange) onChange();
    } catch (err) {
      setErrorMsg(err.message);
    }
  }

  function handleFound(id) {
    if (!window.confirm("Mark this person as found? The cameras stop looking and their face data is deleted.")) return;
    run(() => updateStatus(id, "FOUND"));
  }

  function handleClose(id) {
    if (!window.confirm("Close this report? The cameras stop looking and their face data is deleted. Old sightings stay in the audit log.")) return;
    run(() => deletePerson(id));
  }

  // "Spotted" -> "Still searching" again, for example when a match was a mistake
  function handleNotThem(id) {
    run(() => updateStatus(id, "SEARCHING"));
  }

  function handleAddPhotos(id, e) {
    const files = Array.from(e.target.files);
    e.target.value = "";
    if (files.length === 0) return;
    const formData = new FormData();
    files.forEach((f) => formData.append("photos", f));
    run(async () => {
      const result = await addPhotos(id, formData);
      const used = (result.photoReport || []).filter((r) => r.accepted).length;
      setInfoMsg(`${used} of ${files.length} photo(s) were good enough and added.`);
    });
  }

  if (loading) return <p className="text-slate-400 text-sm">Loading your reports...</p>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
      <h2 className="font-semibold mb-4">Your reports ({persons.length})</h2>
      {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}
      {infoMsg && <p className="text-emerald-400 text-sm mb-3">{infoMsg}</p>}

      <div className="space-y-3">
        {persons.map((p) => {
          const look = STATUS_LOOK[p.status] || STATUS_LOOK.SEARCHING;
          const attrs = p.attributes || {};
          return (
            <div key={p.id} className={"flex items-center justify-between bg-slate-800/50 rounded px-4 py-3 " + (p.active ? "" : "opacity-60")}>
              <div className="flex items-center gap-3">
                {p.photoUrl ? (
                  <img src={fileUrl(p.photoUrl)} alt={p.name} className="w-12 h-12 rounded object-cover" />
                ) : (
                  <div className="w-12 h-12 rounded bg-slate-800" />
                )}
                <div>
                  <div className="text-sm font-medium">{p.name}</div>
                  <div className="text-xs text-slate-400">
                    Age {p.age} - {p.gender} - Reported at: {p.lastSeen}
                  </div>
                  <div className="text-xs text-slate-500">
                    {p.photoCount} photo(s)
                    {attrs.upperColor && ` - top ${attrs.upperColor}`}
                    {attrs.lowerColor && ` - legs ${attrs.lowerColor}`}
                    {attrs.heightCm && ` - ${attrs.heightCm} cm`}
                  </div>
                  <div className="text-xs mt-1">
                    {p.lastSighting ? (
                      <span className="text-emerald-400">
                        Last spotted on {p.lastSighting.camId} at {formatTime(p.lastSighting.timestamp)}
                        {p.lastSighting.status === "POSSIBLE" && " (possible - clothes only)"}
                      </span>
                    ) : (
                      <span className="text-slate-500">Not spotted by any camera yet</span>
                    )}
                  </div>
                  {!p.active && <div className="text-xs text-slate-500 mt-1">Face data deleted. This report is finished.</div>}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className={"text-xs px-2 py-0.5 rounded " + look.css}>{look.text}</span>

                {p.active && (
                  <>
                    <label className="text-slate-500 hover:text-emerald-400 cursor-pointer" title="Add more photos">
                      <ImagePlus size={16} />
                      <input type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleAddPhotos(p.id, e)} />
                    </label>
                    {p.status === "MATCHED" && (
                      <button onClick={() => handleNotThem(p.id)} className="text-xs text-slate-400 hover:text-amber-400" title="The match was wrong">
                        Not them
                      </button>
                    )}
                    <button onClick={() => handleFound(p.id)} className="text-slate-500 hover:text-emerald-400" title="Mark as found">
                      <CheckCircle2 size={16} />
                    </button>
                    <button onClick={() => handleClose(p.id)} className="text-slate-500 hover:text-red-400" title="Close report">
                      <Trash2 size={16} />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}

        {persons.length === 0 && <p className="text-slate-500 text-sm">You have not submitted any reports yet.</p>}
      </div>
    </div>
  );
}
