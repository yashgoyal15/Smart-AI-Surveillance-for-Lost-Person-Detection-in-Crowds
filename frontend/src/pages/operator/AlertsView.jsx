import React, { useEffect, useState } from "react";
import AlertRow from "../../components/AlertRow.jsx";
import { getAlerts } from "../../services/alertService.js";
import { getCameras } from "../../services/cameraService.js";
import { listenToAlerts } from "../../services/alertStream.js";

// slow backup refresh, only needed if the live connection is down
const POLL_MS = Number(import.meta.env.VITE_ALERT_POLL_INTERVAL) || 15000;

export default function AlertsView() {
  const [alerts, setAlerts] = useState([]);
  const [cameraIds, setCameraIds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [camFilter, setCamFilter] = useState("");       // "" means all cameras
  const [statusFilter, setStatusFilter] = useState(""); // "", "MATCH" or "POSSIBLE"
  const [live, setLive] = useState(false);              // is the push connection working?

  // the camera buttons come from the database, so added cameras appear automatically
  useEffect(() => {
    getCameras()
      .then((list) => setCameraIds(list.map((c) => c.id)))
      .catch((err) => setErrorMsg(err.message));
  }, []);

  useEffect(() => {
    async function load() {
      try {
        setAlerts(await getAlerts({ cam: camFilter, status: statusFilter }));
        setErrorMsg("");
      } catch (err) {
        setErrorMsg(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();

    // the server pushes a message when a new alert is saved -> load the list again at once
    const stopListening = listenToAlerts(load, setLive);
    const timer = setInterval(load, POLL_MS);
    return () => {
      stopListening();
      clearInterval(timer);
    };
  }, [camFilter, statusFilter]);

  function FilterButton({ active, onClick, children }) {
    return (
      <button
        onClick={onClick}
        className={
          "px-3 py-1.5 rounded text-xs font-medium " +
          (active ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-300 hover:bg-slate-700")
        }
      >
        {children}
      </button>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        {["", ...cameraIds].map((id) => (
          <FilterButton key={id} active={camFilter === id} onClick={() => setCamFilter(id)}>
            {id === "" ? "All cameras" : id}
          </FilterButton>
        ))}
        <span className="mx-2 text-slate-700">|</span>
        <FilterButton active={statusFilter === ""} onClick={() => setStatusFilter("")}>All</FilterButton>
        <FilterButton active={statusFilter === "MATCH"} onClick={() => setStatusFilter("MATCH")}>Confirmed</FilterButton>
        <FilterButton active={statusFilter === "POSSIBLE"} onClick={() => setStatusFilter("POSSIBLE")}>Possible (clothes)</FilterButton>
        <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-400">
          <span className={"w-2 h-2 rounded-full " + (live ? "bg-emerald-400" : "bg-slate-600")} />
          {live ? "Live" : "Reconnecting..."}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Confirmed = the face matched. Possible = only the clothes or height looked right, so a person should check the picture.
      </p>

      {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}
      {loading && <p className="text-slate-400 text-sm">Loading alerts...</p>}

      <div className="space-y-3">
        {alerts.map((a) => (
          <AlertRow key={a.id} alert={a} />
        ))}
      </div>

      {!loading && alerts.length === 0 && (
        <p className="text-slate-500 text-sm">No sightings yet. Start a camera and register a person to see alerts here.</p>
      )}
    </div>
  );
}
