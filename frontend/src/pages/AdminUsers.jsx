import { useEffect, useMemo, useState } from "react";
import { Activity, Search, ShieldAlert, Users } from "lucide-react";
import { api, formatError, levelColor } from "@/lib/api";

const dateLabel = (value) => value ? new Date(value).toLocaleString() : "No activity yet";

export default function AdminUsers() {
  const [overview, setOverview] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [scans, setScans] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/admin/users")
      .then(({ data }) => {
        setOverview(data);
        setSelectedId(data.users[0]?.id || "");
      })
      .catch((err) => setError(formatError(err)));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setScans([]);
      return;
    }
    api.get(`/admin/users/${selectedId}/scans`)
      .then(({ data }) => setScans(data))
      .catch((err) => setError(formatError(err)));
  }, [selectedId]);

  const shownUsers = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return (overview?.users || []).filter((user) =>
      !needle || `${user.name} ${user.email}`.toLowerCase().includes(needle)
    );
  }, [overview, query]);
  const selectedUser = overview?.users.find((user) => user.id === selectedId);

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.3em] text-cyan-400">Administration</p>
        <h1 className="text-3xl font-bold md:text-4xl">User activity</h1>
        <p className="mt-2 text-slate-400">Review registered accounts and the scans they have run.</p>
      </div>

      {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Registered users", value: overview?.total_users ?? "—", Icon: Users },
          { label: "Scans recorded", value: overview?.total_scans ?? "—", Icon: Activity },
          { label: "Threats flagged", value: overview?.total_threats ?? "—", Icon: ShieldAlert },
        ].map(({ label, value, Icon }) => (
          <div key={label} className="card flex items-center gap-4">
            <Icon className="h-5 w-5 text-cyan-400" />
            <div><p className="text-sm text-slate-400">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p></div>
          </div>
        ))}
      </div>

      <section className="card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h2 className="text-lg font-semibold">Accounts</h2><p className="text-sm text-slate-400">Select an account to review its scan history.</p></div>
          <label className="relative block w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input className="field w-full pl-9 text-sm" placeholder="Search name or email" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[650px] text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
              <tr><th className="p-3">User</th><th className="p-3">Role</th><th className="p-3">Scans</th><th className="p-3">Threats</th><th className="p-3">Last scan</th></tr>
            </thead>
            <tbody>
              {shownUsers.map((user) => (
                <tr key={user.id} onClick={() => setSelectedId(user.id)} className={`cursor-pointer border-b border-slate-800/60 transition-colors hover:bg-slate-800/40 ${selectedId === user.id ? "bg-cyan-500/5" : ""}`}>
                  <td className="p-3"><div className="font-medium">{user.name}</div><div className="text-xs text-slate-400">{user.email}</div></td>
                  <td className="p-3 capitalize text-slate-300">{user.role}</td>
                  <td className="p-3 font-mono">{user.activity.scan_count}</td>
                  <td className="p-3 font-mono text-red-300">{user.activity.threats}</td>
                  <td className="p-3 text-xs text-slate-400">{dateLabel(user.activity.last_scan)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {overview && shownUsers.length === 0 && <p className="py-8 text-center text-sm text-slate-500">No matching users.</p>}
          {!overview && !error && <p className="py-8 text-center text-sm text-slate-500">Loading accounts…</p>}
        </div>
      </section>

      {selectedUser && (
        <section className="card space-y-4">
          <div><p className="text-xs uppercase tracking-wider text-cyan-400">Selected account</p><h2 className="mt-1 text-xl font-semibold">{selectedUser.name}</h2><p className="text-sm text-slate-400">{selectedUser.email}</p></div>
          <div className="space-y-3">
            {scans.map((scan) => (
              <article key={scan.id} className="flex flex-col gap-2 rounded-lg border border-slate-800 p-4 sm:flex-row sm:items-center">
                <span className="w-24 shrink-0 font-mono text-xs uppercase text-cyan-300">{scan.type}</span>
                <div className="min-w-0 flex-1"><p className="truncate text-sm text-slate-200" title={scan.input}>{scan.input}</p><p className="mt-1 text-xs text-slate-500">{dateLabel(scan.created_at)}</p></div>
                <div className="sm:text-right"><p className="text-sm font-medium" style={{ color: levelColor(scan.level) }}>{scan.verdict}</p><p className="font-mono text-xs text-slate-400">Score {scan.score}</p></div>
              </article>
            ))}
            {scans.length === 0 && <p className="py-6 text-center text-sm text-slate-500">No scans recorded for this user.</p>}
          </div>
        </section>
      )}
    </div>
  );
}
