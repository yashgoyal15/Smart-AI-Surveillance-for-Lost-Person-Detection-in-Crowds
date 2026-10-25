import React from "react";
import { useAuth } from "../context/AuthContext.jsx";
import OperatorDashboard from "./OperatorDashboard.jsx";
import ReporterDashboard from "./ReporterDashboard.jsx";

// This page decides WHICH dashboard to show, based on the role that
// was picked on the login page (operator vs reporter).
export default function DashboardPage() {
  const { user } = useAuth();

  if (user?.role === "operator") {
    return <OperatorDashboard />;
  }

  return <ReporterDashboard />;
}
