import { useState } from "react";
import { toast } from "sonner";
import { api, formatError, levelColor } from "@/lib/api";
import { Gauge } from "@/components/Gauge";
import { PdfButton } from "@/components/PdfButton";

const samples = {
  ai: "In today's fast-paced digital landscape, it is important to note that cybersecurity plays a crucial role in protecting organizations. Furthermore, businesses must leverage robust and comprehensive strategies to navigate the ever-evolving threat landscape. Moreover, fostering a holistic security culture is paramount. In conclusion, a multifaceted approach is a testament to an organization's commitment to safety.",
  human: "Honestly I didn't expect the trip to go so badly. We missed the first train, so we just sat at the station eating cold fries for an hour. Then it rained! My brother kept joking that we'd never make it, and he was kinda right. Still, the view from the hill at sunset? Worth every soggy minute. I'd do it again, probably.",
};

const sentColor = (s) => (s >= 65 ? "bg-red-500/20 border-red-500/40" : s >= 40 ? "bg-amber-500/15 border-amber-500/30" : "bg-emerald-500/10 border-emerald-500/25");

export default function AiDetector() {
  const [text, setText] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  const analyze = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/scan/ai", { text });
      setRes(data);
      if (data.level === "insufficient") toast.warning(data.verdict);
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">AI Detector</p>
        <h1 className="text-3xl md:text-4xl font-bold">AI content detector</h1>
        <p className="text-slate-400 mt-2">Paste 20+ words. We analyse rhythm, vocabulary and AI-typical phrasing.</p>
      </div>
      <div className="card">
        <textarea data-testid="ai-content-input" rows={8} className="field resize-y text-sm leading-relaxed" placeholder="Paste text here..." value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex flex-wrap items-center gap-2 mt-4">
          <button data-testid="ai-sample-ai-btn" onClick={() => setText(samples.ai)} className="btn-ghost">AI sample</button>
          <button data-testid="ai-sample-human-btn" onClick={() => setText(samples.human)} className="btn-ghost">Human sample</button>
          <span data-testid="ai-word-count" className="text-xs text-slate-500 ml-2">{words} words · {text.length} chars</span>
          <button data-testid="ai-content-analyze-btn" disabled={busy || !text.trim()} onClick={analyze} className="btn-primary ml-auto">{busy ? "Analysing..." : "Analyse text"}</button>
        </div>
      </div>
      {res && res.level !== "insufficient" && (
        <div className="grid lg:grid-cols-5 gap-6 fade-up">
          <div className="card lg:col-span-2 flex flex-col items-center">
            <Gauge value={res.ai_probability} level={res.level} label="AI likelihood %" testId="ai-gauge-meter" />
            <p data-testid="ai-verdict" className="font-display text-2xl font-bold mt-4" style={{ color: levelColor(res.level) }}>{res.verdict}</p>
            <div className="grid grid-cols-3 gap-3 w-full mt-6 text-center">
              {[["Burstiness", res.metrics.burstiness], ["Vocab", res.metrics.vocabulary_richness], ["Perplexity", res.metrics.perplexity_index]].map(([k, v]) => (
                <div key={k} className="bg-slate-950/60 rounded-lg p-3 border border-slate-800">
                  <p className="font-mono font-semibold">{v}</p>
                  <p className="text-[11px] text-slate-500">{k}</p>
                </div>
              ))}
            </div>
            <ul className="mt-6 space-y-1 text-xs text-slate-400 w-full" data-testid="ai-signals">
              {res.signals.map((s) => <li key={s}>• {s}</li>)}
            </ul>
            <div className="mt-5"><PdfButton scanId={res.scan_id} /></div>
          </div>
          <div className="card lg:col-span-3">
            <h3 className="font-semibold mb-4">Sentence heatmap</h3>
            <div className="space-y-2 max-h-[420px] overflow-y-auto scrollbar-thin pr-1" data-testid="ai-sentence-list">
              {res.sentences.map((s, i) => (
                <div key={i} className={`border rounded-lg p-3 text-sm flex gap-3 ${sentColor(s.score)}`}>
                  <span className="font-mono text-xs text-slate-300 shrink-0 w-9">{s.score}%</span>
                  <span className="text-slate-200">{s.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
