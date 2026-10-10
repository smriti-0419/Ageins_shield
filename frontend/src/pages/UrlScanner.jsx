import { useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { toast } from "sonner";
import { api, formatError, levelColor } from "@/lib/api";
import { Gauge } from "@/components/Gauge";
import { AlarmBanner } from "@/components/AlarmBanner";
import { FlagList } from "@/components/FlagList";
import { PdfButton } from "@/components/PdfButton";
import { CalendarClock, ShieldPlus } from "lucide-react";

const DomainAge = ({ age, trusted }) => {
  let text = "Domain age: lookup unavailable";
  if (trusted) text = "Domain age: well-known trusted domain";
  else if (age?.status === "unregistered") text = "Domain age: no registration record";
  else if (age?.created) {
    const years = (age.age_days / 365).toFixed(1);
    text = `Registered ${age.created} · ${age.age_days < 365 ? `${age.age_days} days` : `${years} years`} old`;
  }
  return (
    <p data-testid="url-domain-age" className="flex items-center gap-2 text-xs text-slate-300 mt-3 bg-slate-950/60 border border-slate-800 rounded-full px-3 py-1.5">
      <CalendarClock className="w-3.5 h-3.5 text-cyan-400" /> {text}
    </p>
  );
};

const presets = [
  { label: "Phishing bank", url: "http://secure-login-paypal.verify-account.xyz/update" },
  { label: "Crypto drainer", url: "http://metamask-airdrop-claim.top/wallet/unlock" },
  { label: "Look-alike", url: "https://www.arnazon.com/deals" },
  { label: "Legit site", url: "https://www.github.com" },
];

export default function UrlScanner() {
  const [url, setUrl] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sound, setSound] = useState(true);
  const [alarm, setAlarm] = useState(false);

  const scan = async (target) => {
    const u = (target ?? url).trim();
    if (!u) return;
    setUrl(u);
    setBusy(true);
    try {
      const { data } = await api.post("/scan/url", { url: u });
      setRes(data);
      setAlarm(data.is_fraud);
      if (data.is_fraud) toast.error(`Fraud alarm: ${data.host} scored ${data.score}/100`);
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };

  const markTrusted = async () => {
    try {
      const { data } = await api.post("/safe-sites", { domain: res.host });
      toast.success(`${data.domain} added to Safe Sites`);
      scan(res.url);
    } catch (e) {
      toast.error(formatError(e));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Fraud Scanner</p>
        <h1 className="text-3xl md:text-4xl font-bold">Website security meter</h1>
        <p className="text-slate-400 mt-2">Paste any link. Scores below 50 trigger the fraud alarm.</p>
      </div>
      {alarm && res && <AlarmBanner score={res.score} host={res.host} soundOn={sound} onDismiss={() => setAlarm(false)} />}
      <div className="card">
        <form onSubmit={(e) => { e.preventDefault(); scan(); }} className="flex flex-col md:flex-row gap-3">
          <input data-testid="url-scan-input" className="field font-mono text-sm" placeholder="https://example.com/login" value={url} onChange={(e) => setUrl(e.target.value)} />
          <button data-testid="url-scan-submit-btn" disabled={busy} className="btn-primary whitespace-nowrap">{busy ? "Scanning..." : "Scan URL"}</button>
        </form>
        <div className="flex flex-wrap items-center gap-2 mt-4">
          {presets.map((p, i) => (
            <button key={p.label} data-testid={`url-preset-${i}`} onClick={() => scan(p.url)} className="btn-ghost">{p.label}</button>
          ))}
          <button data-testid="alarm-sound-toggle" onClick={() => setSound((s) => !s)} className="btn-ghost ml-auto flex items-center gap-2">
            {sound ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />} Siren {sound ? "on" : "off"}
          </button>
        </div>
      </div>
      {res && (
        <div className="grid lg:grid-cols-5 gap-6 fade-up">
          <div className="card lg:col-span-2 flex flex-col items-center justify-center">
            <Gauge value={res.score} level={res.level} />
            <p data-testid="url-scan-verdict" className="font-display text-2xl font-bold mt-4" style={{ color: levelColor(res.level) }}>{res.verdict}</p>
            <p data-testid="url-scan-host" className="font-mono text-xs text-slate-400 mt-2 break-all text-center">{res.host}</p>
            <DomainAge age={res.domain_age} trusted={res.trusted} />
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <PdfButton scanId={res.scan_id} />
              {res.host && !res.trusted && !res.user_trusted && (
                <button data-testid="mark-trusted-btn" onClick={markTrusted} className="btn-ghost flex items-center gap-2">
                  <ShieldPlus className="w-4 h-4" /> Mark as trusted
                </button>
              )}
            </div>
          </div>
          <div className="card lg:col-span-3">
            <h3 className="font-semibold mb-4">Findings ({res.flags.length})</h3>
            <FlagList flags={res.flags} testId="url-flags" />
          </div>
        </div>
      )}
    </div>
  );
}
