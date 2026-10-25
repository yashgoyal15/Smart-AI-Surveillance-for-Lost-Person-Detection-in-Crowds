import React from "react";
import { useNavigate } from "react-router-dom";
import { Camera, ScanFace, FileClock, ShieldAlert } from "lucide-react";
import Navbar from "../components/Navbar.jsx";

// This is the very first page a visitor sees.
// It just introduces the project and has a Sign In button that
// takes the user to the role-selection + login page.
export default function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: Camera,
      title: "Multi-Camera Monitoring",
      text: "Connects to existing CCTV feeds and scans crowds in real time using YOLOv8.",
    },
    {
      icon: ScanFace,
      title: "Face Recognition Matching",
      text: "ArcFace embeddings + FAISS similarity search identify a registered missing person within seconds.",
    },
    {
      icon: FileClock,
      title: "Alerts & Audit Trail",
      text: "Every detection is logged with a confidence score, camera ID and timestamp for accountability.",
    },
  ];

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100">
      <Navbar />

      {/* ---------------- HERO SECTION ---------------- */}
      <section className="px-8 pt-16 pb-20 max-w-3xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-full px-4 py-1.5 text-xs text-emerald-400 mb-6">
          <ShieldAlert size={14} />
          Project ID: 2023CSEPID15 &middot; ABES Institute of Technology
        </div>

        <h1 className="text-4xl font-bold leading-tight">
          Smart AI Surveillance for
          <br />
          <span className="text-emerald-400">Lost Person Detection</span> in Crowds
        </h1>

        <p className="text-slate-400 mt-5 text-sm leading-relaxed">
          In a crowd of thousands, no one should ever be truly lost. This system
          watches live camera feeds, recognizes registered missing persons, and
          alerts the response team in real time.
        </p>

        <button
          onClick={() => navigate("/login")}
          className="mt-8 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm px-6 py-3 rounded transition-colors"
        >
          Sign In to Continue
        </button>
      </section>

      {/* ---------------- FEATURES ---------------- */}
      <section className="px-8 pb-20 max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5">
        {features.map((f) => {
          const Icon = f.icon;
          return (
            <div
              key={f.title}
              className="bg-slate-900 border border-slate-800 rounded-lg p-5"
            >
              <Icon className="text-emerald-400 mb-3" size={22} />
              <h3 className="font-semibold text-sm">{f.title}</h3>
              <p className="text-slate-400 text-xs mt-2 leading-relaxed">
                {f.text}
              </p>
            </div>
          );
        })}
      </section>

      <footer className="px-8 py-6 text-center text-xs text-slate-500 border-t border-slate-800">
        Department of Computer Science &amp; Engineering &middot; Session 2026-27
      </footer>
    </div>
  );
}
