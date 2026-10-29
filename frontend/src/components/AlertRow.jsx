import React from "react";
import { Camera, Clock } from "lucide-react";
import { fileUrl } from "../services/api.js";
import { formatTime, formatPercent } from "../utils/format.js";
import { colorHex } from "../utils/colors.js";

// how the alert was found, in simple words
const METHOD_TEXT = {
  face: "by face",
  track: "followed from an earlier face match",
  appearance: "by clothes only - please check the picture",
};

// small round chip showing a clothes colour
function ColorChip({ label, name }) {
  if (!name) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-400">
      <span className="w-3 h-3 rounded-full border border-slate-600" style={{ background: colorHex(name) }} />
      {label} {name}
    </span>
  );
}

// one row showing a single sighting (used on the Dashboard and the Alerts page)
export default function AlertRow({ alert, compact }) {
  const isPossible = alert.status === "POSSIBLE";
  const attrs = alert.attributes || {};

  return (
    <div
      className={
        "flex items-center justify-between rounded px-4 py-3 " +
        (compact ? "bg-slate-800/40" : "bg-slate-900 border ") +
        (!compact && (isPossible ? "border-amber-500/40" : "border-slate-800"))
      }
    >
      <div className="flex items-center gap-3">
        {/* face picture (or the whole body when no face was seen) */}
        {alert.snapshotUrl || alert.bodySnapshotUrl ? (
          <img
            src={fileUrl(alert.snapshotUrl || alert.bodySnapshotUrl)}
            alt=""
            className="w-10 h-10 rounded object-cover object-top bg-slate-800"
          />
        ) : (
          <div className="w-10 h-10 rounded bg-slate-800" />
        )}
        {!compact && alert.bodySnapshotUrl && (
          <img src={fileUrl(alert.bodySnapshotUrl)} alt="" className="w-10 h-14 rounded object-cover bg-slate-800" />
        )}
        <div>
          <div className="text-sm font-medium flex items-center gap-2">
            {alert.personName}
            {isPossible && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400">POSSIBLE</span>}
          </div>
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <Camera size={12} /> {alert.camId}
            <Clock size={12} /> {formatTime(alert.timestamp)}
          </div>
          {!compact && (
            <div className="flex flex-wrap items-center gap-3 mt-1">
              <span className="text-xs text-slate-500">{METHOD_TEXT[alert.method] || alert.method}</span>
              <ColorChip label="top" name={attrs.upperColor} />
              <ColorChip label="legs" name={attrs.lowerColor} />
              {attrs.heightCm && <span className="text-xs text-slate-400">about {attrs.heightCm} cm</span>}
              {attrs.movement && <span className="text-xs text-slate-400">{attrs.movement}</span>}
            </div>
          )}
        </div>
      </div>
      <div className={"text-sm font-semibold " + (isPossible ? "text-amber-400" : "text-emerald-400")}>
        {formatPercent(alert.confidence)}
      </div>
    </div>
  );
}
