import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bot, Code2, History, LayoutDashboard, Link2, ListChecks, LogOut, Mail, Puzzle, Settings as SettingsIcon, ShieldCheck, ShieldPlus, Video, Users } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const links = [
  { to: "/console", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/console/url", label: "Fraud Scanner", icon: Link2 },
  { to: "/console/bulk", label: "Bulk Scanner", icon: ListChecks },
  { to: "/console/ai", label: "AI Detector", icon: Bot },
  { to: "/console/email", label: "Phishing Email", icon: Mail },
  { to: "/console/deepfake", label: "Deepfake Scanner", icon: Video },
  { to: "/console/history", label: "Scan History", icon: History },
  { to: "/console/safe-sites", label: "Safe Sites", icon: ShieldPlus },
  { to: "/console/embed", label: "Embed Chatbot", icon: Code2 },
  { to: "/console/extension", label: "Extension", icon: Puzzle },
  { to: "/console/settings", label: "Settings", icon: SettingsIcon },
  { to: "/console/admin", label: "User Activity", icon: Users, admin: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const visibleLinks = links.filter((link) => !link.admin || user?.role === "admin");
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 border-r border-slate-800 bg-[#0A0F1C] hidden md:flex flex-col p-5 sticky top-0 h-screen">
        <button data-testid="sidebar-logo" onClick={() => nav("/")} className="flex items-center gap-2 mb-10">
          <ShieldCheck className="w-7 h-7 text-cyan-400" />
          <span className="font-display font-bold text-xl tracking-tight">AgeinsShield</span>
        </button>
        <nav className="space-y-1 flex-1">
          {visibleLinks.map(({ to, label, icon: I, end }) => (
            <NavLink key={to} to={to} end={end} data-testid={`nav-${label.toLowerCase().replace(/\s+/g, "-")}`}
              className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${isActive ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30" : "text-slate-400 hover:text-white hover:bg-slate-800/60 border border-transparent"}`}>
              <I className="w-4 h-4" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 pt-4">
          <p data-testid="sidebar-user-email" className="text-xs text-slate-400 truncate mb-2">{user?.email}</p>
          <button data-testid="logout-btn" onClick={async () => { await logout(); nav("/login"); }} className="btn-ghost w-full flex items-center justify-center gap-2">
            <LogOut className="w-4 h-4" /> Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 grid-bg">
        <div className="md:hidden flex gap-2 overflow-x-auto p-3 border-b border-slate-800">
          {visibleLinks.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `whitespace-nowrap text-xs px-3 py-1.5 rounded-full border ${isActive ? "border-cyan-500 text-cyan-300" : "border-slate-700 text-slate-400"}`}>{label}</NavLink>
          ))}
        </div>
        <div className="p-6 md:p-10 max-w-6xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
