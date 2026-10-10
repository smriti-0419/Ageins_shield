import { useState } from "react";
import { toast } from "sonner";
import { api, formatError, levelColor } from "@/lib/api";
import { Gauge } from "@/components/Gauge";
import { FlagList } from "@/components/FlagList";
import { PdfButton } from "@/components/PdfButton";

const samples = [
  { label: "Account suspension", text: "From: PayPal Security <service@paypal-security-alert.xyz>\nReply-To: help@support-desk.ru\nSubject: URGENT: Your account has been suspended\n\nDear Customer,\n\nWe detected unauthorized activity. Your account will be locked within 24 hours unless you verify your account immediately. Confirm your password and credit card here:\nhttp://paypal-login.verify-account.xyz/secure\n\nFINAL NOTICE!!!" },
  { label: "CEO wire transfer", text: "From: CEO <ceo.office@company-mail.top>\nSubject: Quick favor - confidential\n\nHi, I'm in a meeting and need you to process a wire transfer of $24,500 to a new vendor right away. Also buy 5 gift cards for a client and send me the codes ASAP. Don't call, just email." },
  { label: "Genuine receipt", text: "From: GitHub <noreply@github.com>\nDKIM-Signature: v=1; d=github.com\nSubject: Your GitHub receipt\n\nHi Priya,\n\nThanks for your payment. Your Pro plan has renewed. You can view the receipt in your settings at https://github.com/settings/billing.\n\nThe GitHub Team" },
];

export default function EmailDetector() {
  const [content, setContent] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const analyze = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/scan/email", { content });
      setRes(data);
      if (data.is_phishing) toast.error("Phishing email detected!");
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Phishing Email</p>
        <h1 className="text-3xl md:text-4xl font-bold">Phishing email detector</h1>
        <p className="text-slate-400 mt-2">Paste the full email including headers (From, Reply-To) for best accuracy.</p>
      </div>
      <div className="card">
        <textarea data-testid="phishing-email-input" rows={10} className="field resize-y font-mono text-xs leading-relaxed" placeholder={"From: sender@domain.com\nSubject: ...\n\nEmail body..."} value={content} onChange={(e) => setContent(e.target.value)} />
        <div className="flex flex-wrap gap-2 mt-4">
          {samples.map((s, i) => (
            <button key={s.label} data-testid={`email-sample-${i}`} onClick={() => setContent(s.text)} className="btn-ghost">{s.label}</button>
          ))}
          <button data-testid="phishing-analyze-btn" disabled={busy || !content.trim()} onClick={analyze} className="btn-primary ml-auto">{busy ? "Analysing..." : "Analyse email"}</button>
        </div>
      </div>
      {res && (
        <div className="grid lg:grid-cols-5 gap-6 fade-up">
          <div className="card lg:col-span-2 flex flex-col items-center">
            <Gauge value={res.safety_score} level={res.level} label="Email safety score" testId="email-gauge-meter" />
            <p data-testid="email-verdict" className="font-display text-2xl font-bold mt-4" style={{ color: levelColor(res.level) }}>{res.verdict}</p>
            <p className="text-xs text-slate-400 mt-2">Phishing risk: <span data-testid="email-risk-score" className="font-mono">{res.risk_score}%</span></p>
            {res.sender_domain && <p className="font-mono text-xs text-slate-500 mt-1">Sender: {res.sender_domain}</p>}
            <div className="mt-5"><PdfButton scanId={res.scan_id} /></div>
          </div>
          <div className="card lg:col-span-3">
            <h3 className="font-semibold mb-4">Red flags ({res.flags.length})</h3>
            <FlagList flags={res.flags} testId="email-flags" />
          </div>
        </div>
      )}
    </div>
  );
}
