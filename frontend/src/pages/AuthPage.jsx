import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatError } from "@/lib/api";

export default function AuthPage({ mode, role = "user" }) {
  const isLogin = mode === "login";
  const isAdmin = role === "admin";
  const { user, authenticate } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/console" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const body = isLogin ? { email: form.email, password: form.password, portal: role } : form;
      await authenticate(isLogin ? "/auth/login" : "/auth/register", body);
      nav(isAdmin ? "/console/admin" : "/console");
    } catch (err) {
      setError(formatError(err));
    }
    setBusy(false);
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="min-h-screen grid-bg flex items-center justify-center p-6">
      <form onSubmit={submit} className="card w-full max-w-md fade-up" data-testid={`${mode}-form`}>
        <Link to="/" className="flex items-center gap-2 mb-8">
          <ShieldCheck className="w-6 h-6 text-cyan-400" />
          <span className="font-display font-bold text-lg">AgeinsShield</span>
        </Link>
        <h1 className="text-3xl font-bold mb-1">{isAdmin ? "Admin login" : isLogin ? "User login" : "Create your account"}</h1>
        <p className="text-sm text-slate-400 mb-8">{isAdmin ? "Sign in with your configured administrator account." : isLogin ? "Log in to your security console." : "Start scanning in seconds."}</p>
        <div className="space-y-4">
          {!isLogin && <input data-testid="register-name-input" className="field" placeholder="Full name" value={form.name} onChange={set("name")} required />}
          <input data-testid={`${mode}-email-input`} className="field" type="email" placeholder="Email" value={form.email} onChange={set("email")} required />
          <input data-testid={`${mode}-password-input`} className="field" type="password" placeholder="Password (min 6 chars)" value={form.password} onChange={set("password")} required />
        </div>
        {error && <p data-testid="auth-error" className="text-red-400 text-sm mt-4">{error}</p>}
        <button data-testid={`${mode}-submit-btn`} disabled={busy} className="btn-primary w-full mt-6">
          {busy ? "Please wait..." : isLogin ? "Log in" : "Create account"}
        </button>
        <p className="text-sm text-slate-400 mt-6 text-center">
          {isAdmin ? (
            <Link to="/login" className="text-cyan-400 hover:underline">Choose a different portal</Link>
          ) : (
            <>
              {isLogin ? "No account? " : "Already registered? "}
              <Link data-testid="auth-switch-link" to={isLogin ? "/register/user" : "/login/user"} className="text-cyan-400 hover:underline">
                {isLogin ? "Sign up" : "Log in"}
              </Link>
            </>
          )}
        </p>
        {!isAdmin && <p className="mt-3 text-center text-xs"><Link to="/login" className="text-slate-500 hover:text-slate-300">Choose a different portal</Link></p>}
      </form>
    </div>
  );
}
