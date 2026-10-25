import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Users, ArrowLeft, ShieldAlert } from "lucide-react";
import RoleCard from "../components/RoleCard.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { loginUser, registerUser } from "../services/authService.js";

// The two human actors from our use case diagram.
// (The "AI Engine" actor is the system itself, it never logs in.)
const roles = [
  {
    key: "operator",
    title: "Operator (Security Staff)",
    description: "Monitors live camera feeds, views alerts, tracks people and exports the audit log.",
    icon: ShieldCheck,
  },
  {
    key: "reporter",
    title: "Reporter (Police / Family)",
    description: "Registers a missing person with a photo and tracks the status of the report.",
    icon: Users,
  },
];

const inputClass =
  "w-full mt-1 bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm outline-none focus:border-emerald-500";

export default function LoginPage() {
  // step 1 = choose role, step 2 = enter details
  const [step, setStep] = useState(1);
  const [selectedRole, setSelectedRole] = useState(null);
  // "signin" or "signup"
  const [mode, setMode] = useState("signin");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [operatorCode, setOperatorCode] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const roleInfo = roles.find((r) => r.key === selectedRole);

  function handleRoleSelect(roleKey) {
    setSelectedRole(roleKey);
    setErrorMsg("");
    setStep(2);
  }

  function switchMode() {
    setMode(mode === "signin" ? "signup" : "signin");
    setErrorMsg("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorMsg("");
    setLoading(true);

    try {
      if (mode === "signup") {
        await registerUser(selectedRole, name, email, password, operatorCode);
      }
      // after signing up we log in straight away
      const { token, user } = await loginUser(selectedRole, email, password);
      login(user, token);
      navigate("/dashboard");
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <ShieldAlert className="text-emerald-400" size={22} />
          <span className="font-semibold">Lost Person Detection System</span>
        </div>

        {/* ---------------- STEP 1: choose a role ---------------- */}
        {step === 1 && (
          <div>
            <h1 className="text-lg font-semibold text-center mb-1">Sign in as</h1>
            <p className="text-slate-400 text-sm text-center mb-6">Select your role to continue</p>

            <div className="space-y-3">
              {roles.map((r) => (
                <RoleCard
                  key={r.key}
                  icon={r.icon}
                  title={r.title}
                  description={r.description}
                  onClick={() => handleRoleSelect(r.key)}
                />
              ))}
            </div>
          </div>
        )}

        {/* ---------------- STEP 2: details ---------------- */}
        {step === 2 && (
          <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <button
              onClick={() => setStep(1)}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 mb-4"
            >
              <ArrowLeft size={14} /> Change role
            </button>

            <h2 className="font-semibold mb-1">
              {mode === "signin" ? "Signing in as " : "Creating an account as "}
              <span className="text-emerald-400">{roleInfo.title}</span>
            </h2>
            <p className="text-slate-400 text-xs mb-5">
              {mode === "signin" ? "Enter your credentials below" : "Fill in your details below"}
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" && (
                <div>
                  <label className="text-xs text-slate-400">Full name</label>
                  <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} required />
                </div>
              )}

              <div>
                <label className="text-xs text-slate-400">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="you@example.com"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-slate-400">
                  Password {mode === "signup" && "(at least 8 characters)"}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                  minLength={mode === "signup" ? 8 : undefined}
                  required
                />
              </div>

              {/* security staff need a secret code, otherwise anyone could watch the cameras */}
              {mode === "signup" && selectedRole === "operator" && (
                <div>
                  <label className="text-xs text-slate-400">Operator access code</label>
                  <input
                    value={operatorCode}
                    onChange={(e) => setOperatorCode(e.target.value)}
                    className={inputClass}
                    placeholder="given by your administrator"
                    required
                  />
                </div>
              )}

              {errorMsg && <p className="text-red-400 text-xs">{errorMsg}</p>}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-slate-950 font-semibold text-sm rounded py-2 transition-colors"
              >
                {loading ? "Please wait..." : mode === "signin" ? "Sign In" : "Create account"}
              </button>
            </form>

            <button onClick={switchMode} className="w-full text-xs text-slate-400 hover:text-slate-200 mt-4">
              {mode === "signin" ? "No account yet? Create one" : "Already have an account? Sign in"}
            </button>

            {mode === "signin" && (
              <p className="text-slate-500 text-xs mt-3 text-center">
                Demo: {selectedRole}@demo.com / password123
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
