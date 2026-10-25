import React, { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { getPersons, deletePerson } from "../../services/personService.js";
import { fileUrl } from "../../services/api.js";
import { formatTime } from "../../utils/format.js";

export default function MyReportsView({ refreshKey, onChange }) {
  const [persons, setPersons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  // load again whenever refreshKey changes (after a new report or a delete)
  useEffect(() => {
    getPersons()
      .then(setPersons)
      .catch((err) => setErrorMsg(err.message))
      .finally(() => setLoading(false));
  }, [refreshKey]);

  async function handleDelete(id) {
    if (!window.confirm("Remove this report? The cameras will stop looking for this person.")) return;
    try {
      await deletePerson(id);
      if (onChange) onChange();
    } catch (err) {
      setErrorMsg(err.message);
    }
  }

  if (loading) return <p className="text-slate-400 text-sm">Loading your reports...</p>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
      <h2 className="font-semibold mb-4">Your reports ({persons.length})</h2>
      {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}

      <div className="space-y-3">
        {persons.map((p) => (
          <div key={p.id} className="flex items-center justify-between bg-slate-800/50 rounded px-4 py-3">
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
                <div className="text-xs mt-1">
                  {p.lastSighting ? (
                    <span className="text-emerald-400">
                      Last spotted on {p.lastSighting.camId} at {formatTime(p.lastSighting.timestamp)}
                    </span>
                  ) : (
                    <span className="text-slate-500">Not spotted by any camera yet</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={
                  "text-xs px-2 py-0.5 rounded " +
                  (p.status === "MATCHED" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400")
                }
              >
                {p.status === "MATCHED" ? "Spotted" : "Still searching"}
              </span>
              <button onClick={() => handleDelete(p.id)} className="text-slate-500 hover:text-red-400" title="Remove report">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}

        {persons.length === 0 && <p className="text-slate-500 text-sm">You have not submitted any reports yet.</p>}
      </div>
    </div>
  );
}
