import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Bot, Code2, Gauge as GaugeIcon, Mail, ShieldCheck, Siren } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

const HERO = "https://images.unsplash.com/photo-1549605659-32d82da3a059?crop=entropy&cs=srgb&fm=jpg&q=85&w=1800";

const features = [
  { icon: GaugeIcon, title: "Security Meter 1-100", text: "Score any website on 15+ fraud signals: HTTPS, look-alike domains, risky TLDs, bait keywords." },
  { icon: Siren, title: "Fraud Alarm", text: "Flashing perimeter and siren the instant a scanned site looks fraudulent." },
  { icon: Bot, title: "AI Content Detector", text: "Burstiness, vocabulary and phrase analysis estimate how machine-written a text is." },
  { icon: Mail, title: "Phishing Email Detector", text: "Paste raw emails to catch spoofed senders, urgency tactics and malicious links." },
  { icon: Code2, title: "Embeddable Chatbot", text: "One script tag drops the Aegis assistant into any website, with auto page scoring." },
];

export default function Landing() {
  const { user } = useAuth();
  const nav = useNavigate();
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between px-6 md:px-12 py-5 border-b border-slate-800/80 bg-[#070A12]/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-7 h-7 text-cyan-400" />
          <span className="font-display font-bold text-xl">AgeinsShield</span>
        </div>
        <div className="flex gap-3">
          {user ? (
            <button data-testid="nav-console-btn" onClick={() => nav("/console")} className="btn-primary text-sm">Open Console</button>
          ) : (
            <>
              <Link data-testid="nav-login-btn" to="/login" className="btn-ghost">Log in</Link>
              <Link data-testid="nav-register-btn" to="/login" className="btn-primary text-sm">Get started</Link>
            </>
          )}
        </div>
      </header>

      <section className="relative overflow-hidden">
        <img src={HERO} alt="" className="absolute inset-0 w-full h-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#070A12] via-[#070A12]/90 to-transparent" />
        <div className="relative px-6 md:px-12 py-24 md:py-36 max-w-4xl">
          <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-6 fade-up">Personal fraud-defense console</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05] fade-up" style={{ animationDelay: "80ms" }}>
            Know if a site is a scam <span className="text-cyan-400">before</span> you type a password.
          </h1>
          <p className="text-base md:text-lg text-slate-400 mt-6 max-w-2xl fade-up" style={{ animationDelay: "160ms" }}>
            AgeinsShield scores websites 1-100, sounds an alarm on fraud, flags phishing emails, detects AI-written text, and ships a chatbot you can embed anywhere.
          </p>
          <div className="flex flex-wrap gap-4 mt-10 fade-up" style={{ animationDelay: "240ms" }}>
            <button data-testid="hero-cta-btn" onClick={() => nav(user ? "/console/url" : "/login")} className="btn-primary flex items-center gap-2">
              Scan a website <ArrowRight className="w-4 h-4" />
            </button>
            <button data-testid="hero-embed-btn" onClick={() => nav(user ? "/console/embed" : "/login")} className="btn-ghost px-5">Get embed code</button>
          </div>
        </div>
      </section>

      <section className="px-6 md:px-12 py-20 grid-bg">
        <h2 className="text-2xl sm:text-3xl font-bold mb-12">Five layers of defense</h2>
        <div className="grid md:grid-cols-3 gap-5">
          {features.map(({ icon: I, title, text }, i) => (
            <div key={title} data-testid={`feature-card-${i}`} className={`card fade-up ${i === 0 ? "md:col-span-2" : ""}`} style={{ animationDelay: `${i * 70}ms` }}>
              <I className="w-6 h-6 text-cyan-400 mb-4" />
              <h3 className="font-semibold text-lg mb-2">{title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{text}</p>
            </div>
          ))}
        </div>
      </section>
      <footer className="px-6 md:px-12 py-8 border-t border-slate-800 text-xs text-slate-500">AgeinsShield - rule-based security analysis. Always verify critical decisions.</footer>
    </div>
  );
}
