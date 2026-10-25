import React, { useEffect, useState } from "react";
import { MapPin, ArrowRight } from "lucide-react";
import { getPersons, getTrail } from "../../services/personService.js";
import { getCameras } from "../../services/cameraService.js";
import { fileUrl } from "../../services/api.js";
import { formatTime } from "../../utils/format.js";

// "Track across cameras" use case.
// Pick a registered person and see which cameras spotted them, in order.
export default function TrackView() {
  const [persons, setPersons] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [trail, setTrail] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    Promise.all([getPersons(), getCameras()])
      .then(([p, c]) => {
        setPersons(p);
        setCameras(c);
      })
      .catch((err) => setErrorMsg(err.message));
  }, []);

  async function handleSelect(id) {
    setSelectedId(id);
    setTrail(null);
    try {
      setTrail(await getTrail(id));
    } catch (err) {
      setErrorMsg(err.message);
    }
  }

  function locationOf(camId) {
    const cam = cameras.find((c) => c.id === camId);
    return cam ? cam.location : "";
  }

  // many sightings in a row on the same camera are joined into ONE stop
  // e.g. CAM-03, CAM-03, CAM-03, CAM-01  ->  [CAM-03 (3 sightings), CAM-01 (1 sighting)]
  function buildStops(sightings) {
    const stops = [];
    for (let i = 0; i < sightings.length; i++) {
      const s = sightings[i];
      const last = stops[stops.length - 1];
      if (last && last.camId === s.camId) {
        last.count = last.count + 1;
        last.to = s.timestamp;
        last.snapshotUrl = s.snapshotUrl || last.snapshotUrl;
      } else {
        stops.push({ camId: s.camId, from: s.timestamp, to: s.timestamp, count: 1, snapshotUrl: s.snapshotUrl });
      }
    }
    return stops;
  }

  const stops = trail ? buildStops(trail.sightings) : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* left: list of people */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 h-fit">
        <h2 className="font-semibold text-sm mb-3">Registered persons</h2>
        <div className="space-y-2">
          {persons.map((p) => (
            <button
              key={p.id}
              onClick={() => handleSelect(p.id)}
              className={
                "w-full flex items-center gap-3 text-left rounded px-3 py-2 " +
                (selectedId === p.id ? "bg-emerald-500/10 border border-emerald-500/40" : "bg-slate-800/50 hover:bg-slate-800")
              }
            >
              {p.photoUrl && <img src={fileUrl(p.photoUrl)} alt="" className="w-9 h-9 rounded object-cover" />}
              <div>
                <div className="text-sm">{p.name}</div>
                <div className="text-xs text-slate-400">
                  {p.status === "MATCHED" ? "Spotted" : "Not spotted yet"}
                </div>
              </div>
            </button>
          ))}
          {persons.length === 0 && <p className="text-slate-500 text-xs">No one is registered yet.</p>}
        </div>
      </div>

      {/* right: the route */}
      <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-lg p-5">
        {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}

        {!selectedId && <p className="text-slate-500 text-sm">Select a person to see where they were spotted.</p>}
        {selectedId && !trail && <p className="text-slate-400 text-sm">Loading...</p>}

        {trail && (
          <div>
            <h2 className="font-semibold">{trail.person.name}</h2>
            <p className="text-xs text-slate-400 mb-4">Last reported at: {trail.person.lastSeen}</p>

            {stops.length === 0 ? (
              <p className="text-slate-500 text-sm">This person has not been spotted by any camera yet.</p>
            ) : (
              <div>
                {/* quick route summary: CAM-01 -> CAM-03 */}
                <div className="flex flex-wrap items-center gap-2 mb-5 text-sm">
                  {stops.map((s, i) => (
                    <React.Fragment key={i}>
                      {i > 0 && <ArrowRight size={14} className="text-slate-500" />}
                      <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-xs">{s.camId}</span>
                    </React.Fragment>
                  ))}
                </div>

                <div className="space-y-3">
                  {stops.map((s, i) => (
                    <div key={i} className="flex items-center gap-4 bg-slate-800/50 rounded px-4 py-3">
                      {s.snapshotUrl ? (
                        <img src={fileUrl(s.snapshotUrl)} alt="" className="w-14 h-14 rounded object-cover object-top" />
                      ) : (
                        <div className="w-14 h-14 rounded bg-slate-800" />
                      )}
                      <div className="text-sm">
                        <div className="flex items-center gap-1 font-medium">
                          <MapPin size={14} className="text-emerald-400" />
                          {s.camId} {locationOf(s.camId) && `- ${locationOf(s.camId)}`}
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          {formatTime(s.from)}
                          {s.count > 1 && ` to ${formatTime(s.to)}`} ({s.count} sighting{s.count > 1 ? "s" : ""})
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
