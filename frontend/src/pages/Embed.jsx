import { Copy } from "lucide-react";
import { toast } from "sonner";
import { BACKEND_URL } from "@/lib/api";

const snippet = `<script src="${BACKEND_URL}/api/widget.js" defer></script>`;
const preview = `<!doctype html><html><body style="font-family:system-ui;background:#f8fafc;color:#0f172a;padding:32px">
<h2>Demo Shop</h2><p>This is a sample third-party website. The AgeinsShield chatbot (bottom-right) was added with one script tag.</p>
<p>Click the shield and ask: <b>is this site safe?</b></p>${snippet}</body></html>`;

export default function Embed() {
  const copy = async () => {
    await navigator.clipboard.writeText(snippet).catch(() => {});
    toast.success("Embed snippet copied");
  };
  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Embed</p>
        <h1 className="text-3xl md:text-4xl font-bold">Put the chatbot on any website</h1>
        <p className="text-slate-400 mt-2">Paste this line just before the closing &lt;/body&gt; tag of any HTML page.</p>
      </div>
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs uppercase tracking-wider text-slate-500">HTML snippet</span>
          <button data-testid="copy-embed-btn" onClick={copy} className="btn-primary text-sm flex items-center gap-2 py-2"><Copy className="w-4 h-4" /> Copy snippet</button>
        </div>
        <pre data-testid="embed-code-snippet" className="bg-[#070A12] border border-slate-800 rounded-lg p-4 text-xs text-cyan-300 overflow-x-auto">{snippet}</pre>
        <ul className="text-sm text-slate-400 mt-5 space-y-1">
          <li>• Floating shield chat assistant answers security questions.</li>
          <li>• Auto-scores the host page 1-100 and shows a red alarm bar if it looks fraudulent.</li>
          <li>• Pure HTML/CSS/JS, no dependencies, works on any site.</li>
        </ul>
      </div>
      <div className="card p-0 overflow-hidden">
        <div className="px-4 py-2 border-b border-slate-800 text-xs text-slate-500 font-mono">Live preview · demo-shop.example</div>
        <iframe data-testid="embed-preview-iframe" title="Embed preview" srcDoc={preview} className="w-full h-[560px] bg-white" />
      </div>
    </div>
  );
}
