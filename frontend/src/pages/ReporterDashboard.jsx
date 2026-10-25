import React, { useState } from "react";
import { UserPlus, ClipboardList } from "lucide-react";
import Sidebar from "../components/Sidebar.jsx";
import RegisterPersonView from "./reporter/RegisterPersonView.jsx";
import MyReportsView from "./reporter/MyReportsView.jsx";

// tabs available to the Reporter (Police / Family) actor
const navItems = [
  { key: "register", label: "Register Person", icon: UserPlus },
  { key: "reports", label: "My Reports", icon: ClipboardList },
];

const pageTitles = {
  register: ["Register Missing Person", "Submit details to add them to the recognition database"],
  reports: ["My Reports", "Track the status of everyone you've registered"],
};

export default function ReporterDashboard() {
  const [activeTab, setActiveTab] = useState("register");
  // bumping this number forces MyReportsView to re-read the (mock) data
  const [refreshKey, setRefreshKey] = useState(0);
  const [title, subtitle] = pageTitles[activeTab];

  function refresh() {
    setRefreshKey(refreshKey + 1);
  }

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex">
      <Sidebar
        navItems={navItems}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-6">
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-slate-400 text-sm mt-1">{subtitle}</p>
        </div>

        <div className="px-8 pb-8">
          {activeTab === "register" && (
            <RegisterPersonView onPersonAdded={refresh} />
          )}
          {activeTab === "reports" && (
            <MyReportsView refreshKey={refreshKey} onChange={refresh} />
          )}
        </div>
      </main>
    </div>
  );
}
