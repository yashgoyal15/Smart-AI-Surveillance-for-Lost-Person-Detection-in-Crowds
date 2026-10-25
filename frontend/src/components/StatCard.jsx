import React from "react";

// small reusable box used to show one number + label on the dashboard
export default function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4">
      <Icon className={color} size={20} />
      <div className="text-2xl font-bold mt-3">{value}</div>
      <div className="text-slate-400 text-xs mt-1">{label}</div>
    </div>
  );
}
