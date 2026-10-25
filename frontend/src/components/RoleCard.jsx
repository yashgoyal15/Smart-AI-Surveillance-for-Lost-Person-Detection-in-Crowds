import React from "react";

// a clickable card used in the "select your role" step of login
export default function RoleCard({ icon: Icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-slate-900 border border-slate-800 rounded-lg p-5 hover:border-emerald-500 hover:bg-slate-800/60 transition-colors"
    >
      <Icon className="text-emerald-400 mb-3" size={26} />
      <div className="font-semibold text-slate-100">{title}</div>
      <div className="text-sm text-slate-400 mt-1">{description}</div>
    </button>
  );
}
