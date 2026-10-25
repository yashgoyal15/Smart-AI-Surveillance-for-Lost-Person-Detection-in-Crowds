import React, { useEffect, useState } from "react";
import AlertRow from "../../components/AlertRow.jsx";
import { getAlerts } from "../../services/alertService.js";

const POLL_MS = Number(import.meta.env.VITE_ALERT_POLL_INTERVAL) || 5000;
const CAMERA_IDS = ["CAM-01", "CAM-02", "CAM-03", "CAM-04"];

export default function AlertsView() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  // "" means all cameras
  const [camFilter, setCamFilter] = useState("");

  // reload whenever the camera filter changes, and then keep refreshing
  useEffect(() => {
    async function load() {
      try {
        setAlerts(await getAlerts(camFilter));
        setErrorMsg("");
      } catch (err) {
        setErrorMsg(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [camFilter]);

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {["", ...CAMERA_IDS].map((id) => (
          <button
            key={id}
            onClick={() => setCamFilter(id)}
            className={
              "px-3 py-1.5 rounded text-xs font-medium " +
              (camFilter === id ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-300 hover:bg-slate-700")
            }
          >
            {id === "" ? "All cameras" : id}
          </button>
        ))}
      </div>

      {errorMsg && <p className="text-red-400 text-sm mb-3">{errorMsg}</p>}
      {loading && <p className="text-slate-400 text-sm">Loading alerts...</p>}

      <div className="space-y-3">
        {alerts.map((a) => (
          <AlertRow key={a.id} alert={a} />
        ))}
      </div>

      {!loading && alerts.length === 0 && (
        <p className="text-slate-500 text-sm">
          No sightings yet. Start a camera and register a person to see alerts here.
        </p>
      )}
    </div>
  );
}
