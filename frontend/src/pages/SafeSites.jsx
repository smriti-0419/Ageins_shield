import { useEffect, useState } from "react";
import { ShieldCheck, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";

export default function SafeSites() {
  const [sites, setSites] = useState([]);
  const [domain, setDomain] = useState("");

  const load = () => api.get("/safe-sites").then((r) => setSites(r.data));
  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/safe-sites", { domain });
      toast.success(`${data.domain} added to Safe Sites`);
      setDomain("");
      load();
    } catch (err) {
      toast.error(formatError(err));
    }
  };

  const remove = async (s) => {
    await api.delete(`/safe-sites/${s.id}`);
    toast.success(`${s.domain} removed`);
    load();
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Safe Sites</p>
        <h1 className="text-3xl md:text-4xl font-bold">Your trusted websites</h1>
        <p className="text-slate-400 mt-2">Sites on this list always score at least 90 and never set off the fraud alarm. The whole domain is trusted, including its subdomains.</p>
      </div>
      <form onSubmit={add} className="card flex flex-col md:flex-row gap-3">
        <input data-testid="safe-site-input" className="field font-mono text-sm" placeholder="mycompany.com or https://intranet.mycompany.com" value={domain} onChange={(e) => setDomain(e.target.value)} />
        <button data-testid="safe-site-add-btn" disabled={!domain.trim()} className="btn-primary whitespace-nowrap">Add to Safe Sites</button>
      </form>
      <div className="card p-0">
        {sites.length ? (
          <ul data-testid="safe-sites-list">
            {sites.map((s) => (
              <li key={s.id} data-testid={`safe-site-${s.domain}`} className="flex items-center gap-3 px-5 py-4 border-b border-slate-800/60 last:border-0">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="font-mono text-sm flex-1">{s.domain}</span>
                <span className="text-xs text-slate-500">{new Date(s.created_at).toLocaleDateString()}</span>
                <button data-testid={`safe-site-remove-${s.domain}`} onClick={() => remove(s)}><Trash2 className="w-4 h-4 text-slate-500 hover:text-red-400" /></button>
              </li>
            ))}
          </ul>
        ) : (
          <p data-testid="safe-sites-empty" className="p-8 text-center text-slate-500 text-sm">No trusted sites yet. Add one above, or click "Mark as trusted" on a scan result.</p>
        )}
      </div>
    </div>
  );
}
