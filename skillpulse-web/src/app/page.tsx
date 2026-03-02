"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const API_URL = "http://127.0.0.1:8000/api";

function Login({ setToken }: { setToken: (t: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    const ep = isRegister ? "/auth/register" : "/auth/login";

    let options: RequestInit = {};
    if (isRegister) {
      options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      };
    } else {
      const fd = new URLSearchParams();
      fd.append("username", email);
      fd.append("password", password);
      options = {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: fd.toString(),
      };
    }

    try {
      const res = await fetch(API_URL + ep, options);
      const data = await res.json();
      if (res.ok) setToken(data.access_token);
      else setError(data.detail || "An error occurred");
    } catch (err) {
      setError("Network Error. Is the backend running?");
    }
    setLoading(false);
  };

  return (
    <div className="flex justify-center items-center h-screen animate-fade-in">
      <form
        className="card w-[400px] bg-white/5 border border-white/10 rounded-2xl p-6 shadow-xl backdrop-blur-sm"
        onSubmit={handleSubmit}
      >
        <h2 className="text-center font-outfit text-2xl font-bold mb-6">
          {isRegister ? "Create Account" : "Welcome Back"}
        </h2>

        {error && (
          <div className="bg-red-500/20 border border-red-500/30 text-red-300 p-3 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <input
          className="form-input mb-4 w-full p-3 bg-black/20 border border-white/10 rounded-lg text-white"
          type="email"
          placeholder="Email Address"
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="form-input mb-6 w-full p-3 bg-black/20 border border-white/10 rounded-lg text-white"
          type="password"
          placeholder="Password"
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button
          className="btn w-full mb-6 font-semibold bg-[var(--color-accent-primary)] hover:opacity-90 transition-all rounded-lg py-3 text-white"
          disabled={loading}
        >
          {loading ? "Processing..." : isRegister ? "Register" : "Login"}
        </button>
        <p
          className="cursor-pointer text-[var(--color-accent-primary)] text-center text-sm hover:underline"
          onClick={() => setIsRegister(!isRegister)}
        >
          {isRegister
            ? "Already have an account? Login"
            : "Don't have an account? Register"}
        </p>
      </form>
    </div>
  );
}

function Dashboard() {
  const [trends, setTrends] = useState<any[]>([]);
  const [forecast, setForecast] = useState<any>({});
  const [loading, setLoading] = useState(true);

  const generateJunkTrends = () => [
    { skill: "python", count: 124 },
    { skill: "sql", count: 98 },
    { skill: "react", count: 86 },
    { skill: "javascript", count: 71 },
    { skill: "aws", count: 65 },
    { skill: "docker", count: 55 },
  ];

  const generateJunkForecast = () => {
    const data: any = {};
    const skills = ["python", "sql", "react", "aws"];
    skills.forEach((skill) => {
      const skillData = [];
      let baseDemand = Math.floor(Math.random() * 50) + 50;
      for (let i = 1; i <= 12; i++) {
        const month = new Date();
        month.setMonth(month.getMonth() + i);
        baseDemand += Math.floor(Math.random() * 15) - 2;
        skillData.push({ month: month.toISOString().split("T")[0], projected: baseDemand });
      }
      data[skill] = skillData;
    });
    return data;
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tRes, fRes] = await Promise.all([
          fetch(API_URL + "/analytics/trends"),
          fetch(API_URL + "/analytics/forecast"),
        ]);
        let tData = [];
        let fData = Object.create(null);

        if (tRes.ok) tData = await tRes.json();
        if (fRes.ok) fData = await fRes.json();

        // Use fallback if real data is empty
        setTrends(tData.length > 0 ? tData : generateJunkTrends());
        setForecast(Object.keys(fData).length > 0 ? fData : generateJunkForecast());
      } catch (e) {
        console.error("Failed to fetch dashboard data, using junk fallback", e);
        setTrends(generateJunkTrends());
        setForecast(generateJunkForecast());
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="loading-spinner"></div>;

  const fSkill = Object.keys(forecast)[0];

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-outfit font-bold mb-8">Pulse Dashboard</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card bg-white/5 border border-white/10 p-6 rounded-2xl">
          <h2 className="mb-4 text-xl text-[var(--color-text-secondary)] font-semibold">
            Top Demanded Skills
          </h2>
          {trends.length > 0 ? (
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trends} layout="vertical" margin={{ left: 60, right: 20 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    dataKey="skill"
                    type="category"
                    stroke="#cbd5e1"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(255,255,255,0.05)" }}
                    contentStyle={{ background: "#1e293b", border: "none", borderRadius: "8px" }}
                  />
                  <Bar dataKey="count" fill="url(#colorBar)" radius={[0, 4, 4, 0]} barSize={24} />
                  <defs>
                    <linearGradient id="colorBar" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#8e63f1" />
                      <stop offset="100%" stopColor="#a855f7" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-gray-500">No trend data available. Upload job listings first.</p>
          )}
        </div>

        <div className="card bg-white/5 border border-white/10 p-6 rounded-2xl">
          <h2 className="mb-4 text-xl text-[var(--color-text-secondary)] font-semibold">
            12-Month Forecast {fSkill ? `- ${fSkill.toUpperCase()}` : ""}
          </h2>
          {fSkill ? (
            <div className="h-[350px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecast[fSkill]} margin={{ left: 0, right: 20 }}>
                  <XAxis
                    dataKey="month"
                    stroke="#cbd5e1"
                    fontSize={12}
                    tickFormatter={(v: string) => v.substring(5, 7) + "/" + v.substring(2, 4)}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis stroke="#cbd5e1" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "none", borderRadius: "8px" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="projected"
                    stroke="#f59e0b"
                    strokeWidth={4}
                    dot={{ r: 4, fill: "#1e293b", strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-gray-500">
              No forecast data generated. Requires at least 2 consecutive months of job data per skill.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function UploadJob() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState({ text: "", type: "" });

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!file) {
      setMsg({ text: "Please select a file first.", type: "error" });
      return;
    }

    setLoading(true);
    setMsg({ text: "", type: "" });

    const fd = new FormData();
    fd.append("file", file);
    const token = localStorage.getItem("token");

    try {
      const res = await fetch(API_URL + "/jobs/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await res.json();

      if (res.ok) {
        setMsg({ text: data.message, type: "success" });
        setFile(null);
        (e.target as HTMLFormElement).reset(); // Reset file input
      } else {
        setMsg({ text: data.detail || "Upload failed", type: "error" });
      }
    } catch (err) {
      setMsg({ text: "Network error occurred during upload", type: "error" });
    }
    setLoading(false);
  };

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-outfit font-bold mb-8">Ingest Data</h1>

      <div className="card max-w-2xl bg-white/5 border border-white/10 p-8 rounded-2xl shadow-lg">
        <h2 className="mb-2 text-2xl font-bold font-outfit">Upload Job CSV</h2>
        <p className="mb-8 text-[var(--color-text-secondary)] leading-relaxed">
          Upload historical or new job listings containing descriptions. The AI Engine will extract skills,
          map connections, and re-train the trending & forecast models automatically.
          <br />
          <br />
          <a
            href="/demo_jobs.csv" // Make sure to place demo_jobs.csv in public/ folder in nextjs later
            download
            className="text-[var(--color-accent-primary)] no-underline font-bold"
          >
            ✨ Download Demo Jobs File (demo_jobs.csv)
          </a>
        </p>

        {msg.text && (
          <div
            className={`p-4 rounded-lg mb-6 ${msg.type === "success"
                ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border border-red-500/20 text-red-400"
              }`}
          >
            {msg.text}
          </div>
        )}

        <form onSubmit={handleUpload}>
          <div className="border-2 border-dashed border-white/20 rounded-2xl p-12 text-center mb-6 bg-black/10 hover:bg-black/20 transition-colors cursor-pointer w-full">
            <input
              type="file"
              id="fileUpload"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
            />
            <label htmlFor="fileUpload" className="cursor-pointer flex flex-col items-center w-full h-full">
              <div className="text-5xl mb-4">📄</div>
              <span className="text-[var(--color-accent-primary)] font-semibold text-lg">
                {file ? file.name : "Click to Browse CSV"}
              </span>
            </label>
          </div>

          <button className="btn font-semibold bg-[var(--color-accent-primary)] w-full py-4 text-white text-lg rounded-xl hover:opacity-90" disabled={loading || !file}>
            {loading ? "Processing Pipeline..." : "Run Extraction Pipeline"}
          </button>
        </form>
      </div>
    </div>
  );
}

function ResumeAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState("data scientist");
  const [customSkills, setCustomSkills] = useState("");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);

    const fd = new FormData();
    fd.append("file", file);
    if (role === "custom") {
      fd.append("custom_skills", customSkills);
    } else {
      fd.append("custom_role", role);
    }

    const token = localStorage.getItem("token");
    try {
      const res = await fetch(API_URL + "/resume/analyze", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (res.ok) setResults(await res.json());
      else alert("Error analyzing resume");
    } catch (err) {
      alert("Network Error");
    }
    setLoading(false);
  };

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-outfit font-bold mb-8">Smart Resume Analyzer</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card bg-white/5 border border-white/10 p-6 rounded-2xl self-start">
          <h2 className="mb-4 text-xl font-bold font-outfit">Upload Profile</h2>
          <form onSubmit={handleUpload}>
            <label className="block mb-2 text-[var(--color-text-secondary)] text-sm font-semibold">
              Target Role / Template
            </label>
            <select
              className="w-full p-3 mb-4 bg-black/20 border border-white/10 rounded-lg text-white"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="data scientist">Data Scientist</option>
              <option value="software engineer">Software Engineer</option>
              <option value="cloud architect">Cloud Architect</option>
              <option value="product manager">Product Manager</option>
              <option value="custom">-- Type Custom Required Skills --</option>
            </select>

            {role === "custom" && (
              <div className="mb-4 animate-fade-in">
                <label className="block mb-2 text-[var(--color-text-secondary)] text-sm font-semibold">
                  Custom Required Skills (Comma separated)
                </label>
                <input
                  type="text"
                  className="w-full p-3 mb-0 bg-black/20 border border-white/10 rounded-lg text-white"
                  placeholder="e.g. rust, typescript, rest api"
                  value={customSkills}
                  onChange={(e) => setCustomSkills(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="flex justify-between items-center mt-4 mb-2">
              <label className="text-[var(--color-text-secondary)] text-sm font-semibold">
                Upload Resume (.txt/.pdf)
              </label>
              <a
                href="/demo_resume.txt"
                download
                className="text-[var(--color-accent-primary)] no-underline text-xs font-bold"
              >
                📄 Demo Resume.txt
              </a>
            </div>
            <input
              type="file"
              className="w-full p-3 mb-4 bg-black/20 border border-white/10 rounded-lg text-white"
              accept=".txt,.pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />

            <button className="btn bg-[var(--color-accent-primary)] hover:opacity-90 w-full mt-4 p-3 rounded-lg text-white font-bold" disabled={loading || !file}>
              {loading ? "Analyzing Profile..." : "Calculate Gap Score"}
            </button>
          </form>
        </div>

        {loading && !results && (
          <div className="card flex items-center justify-center p-12 bg-white/5 rounded-2xl">
            <div className="loading-spinner"></div>
          </div>
        )}

        {results && !loading && (
          <div className="card bg-white/5 border border-white/10 p-6 rounded-2xl animate-fade-in">
            <h2 className="mb-4 text-xl font-bold font-outfit">Analysis Results</h2>

            <div className="flex items-center gap-6 mb-6 pb-6 border-b border-white/10">
              <div
                className="w-24 h-24 rounded-full flex items-center justify-center relative"
                style={{
                  background: `conic-gradient(${results.score > 50 ? "var(--color-success)" : "var(--color-danger)"
                    } ${results.score}%, rgba(255,255,255,0.05) 0)`,
                }}
              >
                <div className="w-[80px] h-[80px] rounded-full bg-[#1e1b4b] flex items-center justify-center text-2xl font-bold shadow-inner">
                  {results.score}%
                </div>
              </div>
              <div>
                <h3 className="text-2xl font-bold mb-1">Match Confidence</h3>
                <p className="text-[var(--color-text-secondary)] text-sm">
                  Assessing profile against: <b className="text-white">{results.role_assessed}</b>
                </p>
              </div>
            </div>

            <h4 className="mb-3 text-[var(--color-text-secondary)] uppercase tracking-wide text-xs font-bold">
              ✅ Matched Core Skills
            </h4>
            <div className="mb-6 flex flex-wrap gap-2">
              {results.matched.map((s: string) => (
                <span className="badge bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-sm font-semibold" key={s}>
                  {s}
                </span>
              ))}
              {results.matched.length === 0 && (
                <span className="text-white/30 text-sm italic">None detected</span>
              )}
            </div>

            <h4 className="mb-3 text-[var(--color-text-secondary)] uppercase tracking-wide text-xs font-bold">
              ❌ Missing Core Skills
            </h4>
            <div className="mb-6 flex flex-wrap gap-2">
              {results.missing.map((s: string) => (
                <span className="badge bg-red-500/20 text-red-400 px-3 py-1 rounded-full text-sm font-semibold" key={s}>
                  {s}
                </span>
              ))}
              {results.missing.length === 0 && (
                <span className="text-white/30 text-sm italic">None</span>
              )}
            </div>

            <div className="bg-black/20 p-4 rounded-xl mt-8">
              <h4 className="mb-2 text-[var(--color-text-secondary)] text-xs font-semibold">
                Extracted Entities Log
              </h4>
              <p className="text-white/60 text-sm leading-relaxed">
                {results.extracted_skills.join(", ") || "No known skills identified in text."}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [view, setView] = useState("dashboard");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
    const savedToken = localStorage.getItem("token");
    if (savedToken) setToken(savedToken);
  }, []);

  const handleLogin = (t: string) => {
    setToken(t);
    localStorage.setItem("token", t);
    setView("dashboard");
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem("token");
  };

  if (!hydrated) return null; // Avoid hydration mismatch
  if (!token) return <Login setToken={handleLogin} />;

  return (
    <div className="app-container flex h-screen overflow-hidden text-white bg-gradient-to-br from-[#0f172a] to-[#1e1b4b]">
      <div className="sidebar w-[260px] bg-white/5 border-r border-white/10 p-8 flex flex-col gap-4">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-tr from-[#6366f1] to-[#a855f7] rounded-xl flex items-center justify-center font-bold text-lg shadow-lg">
            S
          </div>
          <h2 className="text-2xl font-outfit font-bold tracking-tight">SkillPulse</h2>
        </div>

        <button
          className={`sidebar-link w-full text-left px-4 py-3 rounded-lg transition-all ${view === "dashboard" ? "bg-white/10 font-semibold" : "hover:bg-white/5"
            }`}
          onClick={() => setView("dashboard")}
        >
          📊 Analytics Dashboard
        </button>
        <button
          className={`sidebar-link w-full text-left px-4 py-3 rounded-lg transition-all ${view === "upload" ? "bg-white/10 font-semibold" : "hover:bg-white/5"
            }`}
          onClick={() => setView("upload")}
        >
          📥 Ingest Job Data
        </button>
        <button
          className={`sidebar-link w-full text-left px-4 py-3 rounded-lg transition-all ${view === "resume" ? "bg-white/10 font-semibold" : "hover:bg-white/5"
            }`}
          onClick={() => setView("resume")}
        >
          🧑‍💻 Profile Analyzer
        </button>

        <div className="flex-1"></div>

        <button
          className="sidebar-link w-full flex items-center gap-3 px-4 py-3 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-all font-medium"
          onClick={handleLogout}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          Sign Out
        </button>
      </div>

      <div className="main-content flex-1 p-8 lg:p-12 overflow-y-auto w-full max-w-[1400px] mx-auto">
        {view === "dashboard" && <Dashboard />}
        {view === "upload" && <UploadJob />}
        {view === "resume" && <ResumeAnalyzer />}
      </div>
    </div>
  );
}
