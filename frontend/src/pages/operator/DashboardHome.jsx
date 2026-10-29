import React, { useEffect, useState } from "react";
import { Users, CheckCircle2, Camera, Activity, Bell, HelpCircle } from "lucide-react";
import StatCard from "../../components/StatCard.jsx";
import AlertRow from "../../components/AlertRow.jsx";
import { getAlerts, getDashboardStats } from "../../services/alertService.js";
import { getCameras } from "../../services/cameraService.js";
import { listenToAlerts } from "../../services/alertStream.js";

// the server pushes new alerts, so this slow refresh is only a backup (camera status, etc.)
const POLL_MS = Number(import.meta.env.VITE_ALERT_POLL_INTERVAL) || 10000;

export default function DashboardHome() {
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    async function loadDashboard() {
      try {
        // ask for all 3 things at the same time instead of one after another
        const [statsData, alertsData, camerasData] = await Promise.all([
          getDashboardStats(),
          getAlerts(),
          getCameras(),
        ]);
        setStats(statsData);
        setAlerts(alertsData);
        setCameras(camerasData);
        setErrorMsg("");
      } catch (err) {
        setErrorMsg(err.message);
      }
    }

    loadDashboard();
    const timer = setInterval(loadDashboard, POLL_MS);
    const stopListening = listenToAlerts(loadDashboard); // reload the moment a new alert arrives
    return () => {
      clearInterval(timer);
      stopListening();
    };
  }, []);

  if (errorMsg) return <p className="text-red-400 text-sm">{errorMsg}</p>;
  if (!stats) return <p className="text-slate-400 text-sm">Loading dashboard...</p>;

  const statCards = [
    { label: "Registered Persons", value: stats.registeredPersons, icon: Users, color: "text-sky-400" },
    { label: "Matches (last 24 hours)", value: stats.matches24h, icon: CheckCircle2, color: "text-emerald-400" },
    { label: "Possible (clothes only)", value: stats.possible24h, icon: HelpCircle, color: "text-amber-400" },
    { label: "Cameras Online", value: `${stats.camerasOnline}/${stats.camerasTotal}`, icon: Camera, color: "text-amber-400" },
    { label: "Avg. Match Confidence", value: `${stats.avgConfidence}%`, icon: Activity, color: "text-fuchsia-400" },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      <p className="text-xs text-slate-500 mt-3">
        A face counts as a match when its similarity is {Math.round(stats.threshold * 100)}% or higher.
        {stats.stillSearching > 0 && ` ${stats.stillSearching} person(s) not spotted yet.`}
        {` ${stats.found} found, ${stats.closed} closed.`}
      </p>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Bell size={16} className="text-emerald-400" />
            Recent Sightings
          </h2>
          <div className="space-y-3">
            {alerts.slice(0, 5).map((a) => (
              <AlertRow key={a.id} alert={a} compact />
            ))}
            {alerts.length === 0 && <p className="text-slate-500 text-sm">Nothing spotted yet.</p>}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Camera size={16} className="text-emerald-400" />
            Camera Status
          </h2>
          <div className="space-y-3">
            {cameras.map((c) => (
              <div key={c.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-300">
                  {c.id} - {c.location}
                </span>
                <span
                  className={
                    "px-2 py-0.5 rounded text-xs " +
                    (c.status === "online" ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-700/40 text-slate-400")
                  }
                >
                  {c.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
