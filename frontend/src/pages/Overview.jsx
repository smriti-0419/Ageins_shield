import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Bot, Link2, Mail, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const tools = [
  { to: "/console/url", icon: Link2, title: "Fraud Scanner", text: "Rate any website 1-100 with alarm." },
  { to: "/console/ai", icon: Bot, title: "AI Detector", text: "Estimate AI-written likelihood." },
  { to: "/console/email", icon: Mail, title: "Phishing Email", text: "Spot spoofed & scam emails." },
];

export default function Overview() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  useEffect(() => { api.get("/stats").then((r) => setStats(r.data)); }, []);
  const tiles = [
    { label: "Total scans", value: stats?.total ?? "-", icon: Activity, testId: "stat-total" },
    { label: "Threats caught", value: stats?.threats ?? "-", icon: ShieldAlert, testId: "stat-threats", accent: "text-red-400" },
    { label: "URL scans", value: stats?.by_type?.url ?? "-", icon: Link2, testId: "stat-url" },
    { label: "Email scans", value: stats?.by_type?.email ?? "-", icon: Mail, testId: "stat-email" },
  ];
  return (
    <div>
      <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Console</p>
      <h1 className="text-3xl md:text-4xl font-bold mb-2" data-testid="overview-greeting">Hello, {user?.name}</h1>
      <p className="text-slate-400 mb-10">Your threat surface at a glance.</p>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {tiles.map(({ label, value, icon: I, testId, accent }, i) => (
          <div key={label} className="card fade-up" style={{ animationDelay: `${i * 60}ms` }}>
            <I className={`w-5 h-5 mb-3 ${accent || "text-cyan-400"}`} />
            <p data-testid={testId} className="text-3xl font-display font-bold">{value}</p>
            <p className="text-xs text-slate-400 mt-1">{label}</p>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-3 gap-4">
        {tools.map(({ to, icon: I, title, text }) => (
          <Link key={to} to={to} data-testid={`overview-tool-${title.toLowerCase().replace(/\s+/g, "-")}`} className="card group">
            <I className="w-6 h-6 text-cyan-400 mb-4 group-hover:scale-110 transition-transform" />
            <h3 className="font-semibold mb-1">{title}</h3>
            <p className="text-sm text-slate-400">{text}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
