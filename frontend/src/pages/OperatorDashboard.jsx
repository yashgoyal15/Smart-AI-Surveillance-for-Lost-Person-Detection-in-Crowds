import React, { useState } from "react";
import { LayoutDashboard, Bell, Camera, FileText, MapPin } from "lucide-react";
import Sidebar from "../components/Sidebar.jsx";
import DashboardHome from "./operator/DashboardHome.jsx";
import AlertsView from "./operator/AlertsView.jsx";
import CamerasView from "./operator/CamerasView.jsx";
import TrackView from "./operator/TrackView.jsx";
import AuditView from "./operator/AuditView.jsx";

// tabs for the Operator (Security Staff) actor
const navItems = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "cameras", label: "Camera Feeds", icon: Camera },
  { key: "alerts", label: "Live Alerts", icon: Bell },
  { key: "track", label: "Track Person", icon: MapPin },
  { key: "audit", label: "Audit Log", icon: FileText },
];

const pageTitles = {
  dashboard: ["Dashboard", "Live overview of the surveillance system"],
  cameras: ["Camera Feeds", "Start or stop each of the 4 cameras and watch the live video"],
  alerts: ["Live Alerts", "Registered people spotted by the cameras"],
  track: ["Track Person", "See which cameras spotted a person, in order"],
  audit: ["Audit Log", "Every sighting, saved for accountability"],
};

export default function OperatorDashboard() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [title, subtitle] = pageTitles[activeTab];

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex">
      <Sidebar navItems={navItems} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 overflow-y-auto">
        <div className="px-8 pt-8 pb-6">
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-slate-400 text-sm mt-1">{subtitle}</p>
        </div>

        <div className="px-8 pb-8">
          {activeTab === "dashboard" && <DashboardHome />}
          {activeTab === "cameras" && <CamerasView />}
          {activeTab === "alerts" && <AlertsView />}
          {activeTab === "track" && <TrackView />}
          {activeTab === "audit" && <AuditView />}
        </div>
      </main>
    </div>
  );
}
