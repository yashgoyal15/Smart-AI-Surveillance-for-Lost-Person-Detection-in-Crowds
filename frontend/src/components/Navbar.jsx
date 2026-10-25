import React from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

// top navbar shown only on the public landing page
export default function Navbar() {
  const navigate = useNavigate();

  return (
    <header className="w-full flex items-center justify-between px-8 py-5">
      <div className="flex items-center gap-2">
        <ShieldAlert className="text-emerald-400" size={22} />
        <span className="font-semibold text-slate-100">
          Lost Person Detection System
        </span>
      </div>

      <button
        onClick={() => navigate("/login")}
        className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm px-4 py-2 rounded transition-colors"
      >
        Sign In
      </button>
    </header>
  );
}
