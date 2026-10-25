import React from "react";
import { ShieldAlert, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useNavigate } from "react-router-dom";

// Sidebar used inside both dashboards.
// navItems is passed in as a prop so Operator and Reporter can each
// show their own set of tabs while reusing the same component.
export default function Sidebar({ navItems, activeTab, setActiveTab }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <aside className="w-60 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col">
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldAlert className="text-emerald-400" size={22} />
          <span className="font-semibold text-sm leading-tight">
            Lost Person
            <br />
            Detection System
          </span>
        </div>
      </div>

      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.key;
          return (
            <button
              key={item.key}
              onClick={() => setActiveTab(item.key)}
              className={
                "w-full flex items-center gap-3 px-5 py-3 text-sm transition-colors " +
                (isActive
                  ? "bg-emerald-500/10 text-emerald-400 border-r-2 border-emerald-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50")
              }
            >
              <Icon size={17} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800">
        <div className="text-xs text-slate-400 mb-2">
          Logged in as
          <br />
          <span className="text-slate-200">{user?.name}</span> ({user?.role})
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-red-400"
        >
          <LogOut size={14} /> Log out
        </button>
      </div>
    </aside>
  );
}
