import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, levelColor } from "@/lib/api";
import { PdfButton } from "@/components/PdfButton";

const types = ["all", "url", "ai", "email"];

export default function History() {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");

  const load = () => api.get("/history").then((r) => setRows(r.data));
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    await api.delete(`/history/${id}`);
    toast.success("Scan deleted");
    load();
  };

  const shown = rows.filter((r) => (filter === "all" || r.type === filter) && r.input.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">History</p>
        <h1 className="text-3xl md:text-4xl font-bold">Scan history</h1>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        {types.map((t) => (
          <button key={t} data-testid={`history-filter-${t}`} onClick={() => setFilter(t)} className={`btn-ghost uppercase ${filter === t ? "border-cyan-500 text-cyan-300" : ""}`}>{t}</button>
        ))}
        <input data-testid="history-search-input" className="field max-w-xs ml-auto text-sm" placeholder="Search..." value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="card p-0 overflow-x-auto">
        <table data-testid="scan-history-table" className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wider text-slate-500 border-b border-slate-800">
            <tr><th className="p-4">Type</th><th className="p-4">Input</th><th className="p-4">Score</th><th className="p-4">Verdict</th><th className="p-4">Date</th><th className="p-4" /></tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id} data-testid={`history-row-${r.id}`} className="border-b border-slate-800/60 hover:bg-slate-800/30 transition-colors">
                <td className="p-4"><span className="font-mono text-[11px] uppercase px-2 py-1 rounded bg-slate-800 text-cyan-300">{r.type}</span></td>
                <td className="p-4 max-w-xs truncate font-mono text-xs text-slate-300">{r.input}</td>
                <td className="p-4 font-mono font-semibold" style={{ color: levelColor(r.level) }}>{r.score}</td>
                <td className="p-4" style={{ color: levelColor(r.level) }}>{r.verdict}</td>
                <td className="p-4 text-xs text-slate-500 whitespace-nowrap">{new Date(r.created_at).toLocaleString()}</td>
                <td className="p-4"><div className="flex items-center gap-3"><PdfButton compact scanId={r.id} testId={`history-pdf-${r.id}`} /><button data-testid={`history-delete-${r.id}`} onClick={() => remove(r.id)}><Trash2 className="w-4 h-4 text-slate-500 hover:text-red-400" /></button></div></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!shown.length && <p data-testid="history-empty" className="p-8 text-center text-slate-500 text-sm">No scans yet. Run a scan to see it here.</p>}
      </div>
    </div>
  );
}
