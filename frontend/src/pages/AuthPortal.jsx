import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, UserRound, Users } from "lucide-react";

export default function AuthPortal() {
  return (
    <div className="min-h-screen grid-bg flex items-center justify-center p-6">
      <div className="card w-full max-w-2xl fade-up">
        <Link to="/" className="mb-8 flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-cyan-400" />
          <span className="font-display text-lg font-bold">AgeinsShield</span>
        </Link>
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.3em] text-cyan-400">Secure access</p>
        <h1 className="text-3xl font-bold">Choose your portal</h1>
        <p className="mt-2 text-sm text-slate-400">Select how you want to sign in.</p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Link to="/login/admin" className="group rounded-xl border border-slate-700 bg-slate-950/40 p-6 transition-colors hover:border-cyan-500/60 hover:bg-cyan-500/5">
            <Users className="h-7 w-7 text-cyan-400" />
            <h2 className="mt-5 text-xl font-semibold">Admin</h2>
            <p className="mt-2 min-h-10 text-sm text-slate-400">Sign in to manage user activity and review scans.</p>
            <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-cyan-300">Admin login <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
          </Link>

          <Link to="/login/user" className="group rounded-xl border border-slate-700 bg-slate-950/40 p-6 transition-colors hover:border-cyan-500/60 hover:bg-cyan-500/5">
            <UserRound className="h-7 w-7 text-cyan-400" />
            <h2 className="mt-5 text-xl font-semibold">User</h2>
            <p className="mt-2 min-h-10 text-sm text-slate-400">Sign in or create a user account to use the scanners.</p>
            <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-cyan-300">Continue as user <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></span>
          </Link>
        </div>

        <p className="mt-7 text-center text-xs text-slate-500">Administrator accounts are created from the server configuration.</p>
      </div>
    </div>
  );
}
