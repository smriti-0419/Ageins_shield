import { useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { api, formatError, levelColor } from "@/lib/api";
import { PdfButton } from "@/components/PdfButton";

const SAMPLE = "https://www.github.com\npaypa1.com/login\nhttp://arnazon-deals.top/claim\nhttps://en.wikipedia.org\nhttp://g00gle-verify.xyz/account";

const toCsv = (rows) =>
  ["url,host,score,verdict", ...rows.map((r) => [r.url, r.host, r.score, r.verdict].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))].join("\n");

export default function BulkScanner() {
  const [text, setText] = useState("");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const urls = text.split(/[\n,\s]+/).map((u) => u.trim()).filter(Boolean);

  const scan = async () => {
    if (urls.length > 25) return toast.error("Maximum 25 links per scan");
    setBusy(true);
    try {
      const { data } = await api.post("/scan/bulk", { urls });
      setData(data);
      if (data.summary.danger) toast.error(`${data.summary.danger} dangerous link(s) found`);
      else toast.success("Bulk scan complete");
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };

  const exportCsv = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([toCsv(data.results)], { type: "text/csv" }));
    a.download = "ageinsshield-bulk-scan.csv";
    a.click();
  };

  const sorted = data ? [...data.results].sort((a, b) => a.score - b.score) : [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Bulk Scanner</p>
        <h1 className="text-3xl md:text-4xl font-bold">Scan many links at once</h1>
        <p className="text-slate-400 mt-2">One link per line (up to 25). Riskiest results are listed first.</p>
      </div>
      <div className="card">
        <textarea data-testid="bulk-urls-input" rows={7} className="field font-mono text-xs resize-y" placeholder={"https://example.com\nsuspicious-site.xyz"} value={text} onChange={(e) => setText(e.target.value)} />
        <div className="flex flex-wrap items-center gap-2 mt-4">
          <button data-testid="bulk-sample-btn" onClick={() => setText(SAMPLE)} className="btn-ghost">Load sample links</button>
          <span data-testid="bulk-url-count" className={`text-xs ml-2 ${urls.length > 25 ? "text-red-400" : "text-slate-500"}`}>{urls.length} / 25 links</span>
          <button data-testid="bulk-scan-btn" disabled={busy || !urls.length} onClick={scan} className="btn-primary ml-auto">{busy ? "Scanning..." : "Scan all"}</button>
        </div>
      </div>
      {data && <BulkResults data={data} rows={sorted} onExport={exportCsv} />}
    </div>
  );
}

const BulkResults = ({ data, rows, onExport }) => (
  <div className="space-y-4 fade-up">
    <div className="grid grid-cols-3 gap-4">
      {[["safe", "Safe"], ["moderate", "Caution"], ["danger", "Dangerous"]].map(([k, label]) => (
        <div key={k} className="card py-4">
          <p data-testid={`bulk-summary-${k}`} className="text-3xl font-display font-bold" style={{ color: levelColor(k) }}>{data.summary[k]}</p>
          <p className="text-xs text-slate-400">{label}</p>
        </div>
      ))}
    </div>
    <div className="card p-0 overflow-x-auto">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <span className="text-sm font-semibold">{data.total} links scanned</span>
        <button data-testid="bulk-export-csv-btn" onClick={onExport} className="btn-ghost flex items-center gap-2"><Download className="w-4 h-4" /> Export CSV</button>
      </div>
      <table data-testid="bulk-results-table" className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-800">
          <tr><th className="p-4">Website</th><th className="p-4">Score</th><th className="p-4">Verdict</th><th className="p-4">Top finding</th><th className="p-4" /></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.url} data-testid={`bulk-row-${i}`} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
              <td className="p-4 font-mono text-xs max-w-xs truncate">{r.host || r.url}</td>
              <td className="p-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold w-8" style={{ color: levelColor(r.level) }}>{r.score}</span>
                  <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden"><div className="h-full" style={{ width: `${r.score}%`, background: levelColor(r.level) }} /></div>
                </div>
              </td>
              <td className="p-4" style={{ color: levelColor(r.level) }}>{r.verdict}</td>
              <td className="p-4 text-xs text-slate-400">{r.flags.find((f) => f.severity === "high")?.title || r.flags[0]?.title || "None"}</td>
              <td className="p-4"><PdfButton compact scanId={r.scan_id} testId={`bulk-pdf-${i}`} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);
