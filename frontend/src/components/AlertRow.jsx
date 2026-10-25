import React from "react";
import { Camera, Clock } from "lucide-react";
import { fileUrl } from "../services/api.js";
import { formatTime, formatPercent } from "../utils/format.js";

// one row showing a single sighting (used on the Dashboard and the Alerts page)
export default function AlertRow({ alert, compact }) {
  return (
    <div
      className={
        "flex items-center justify-between rounded px-4 py-3 " +
        (compact ? "bg-slate-800/40" : "bg-slate-900 border border-slate-800")
      }
    >
      <div className="flex items-center gap-3">
        {/* picture of the person taken from the camera at that moment */}
        {alert.snapshotUrl ? (
          <img src={fileUrl(alert.snapshotUrl)} alt="" className="w-10 h-10 rounded object-cover object-top bg-slate-800" />
        ) : (
          <div className="w-10 h-10 rounded bg-slate-800" />
        )}
        <div>
          <div className="text-sm font-medium">{alert.personName}</div>
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <Camera size={12} /> {alert.camId}
            <Clock size={12} /> {formatTime(alert.timestamp)}
          </div>
        </div>
      </div>
      <div className="text-sm font-semibold text-emerald-400">{formatPercent(alert.confidence)}</div>
    </div>
  );
}
