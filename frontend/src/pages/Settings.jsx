import { useEffect, useState } from "react";
import { Mail, Send } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { api, formatError } from "@/lib/api";

export default function Settings() {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/settings").then((r) => setS(r.data)); }, []);

  const toggle = async (weekly_email) => {
    const { data } = await api.put("/settings", { weekly_email });
    setS(data);
    toast.success(weekly_email ? "Weekly summary turned on" : "Weekly summary turned off");
  };

  const sendNow = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/digest/preview");
      toast.success(`Summary sent to ${data.to}`);
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };

  if (!s) return <p className="text-slate-400">Loading...</p>;
  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Settings</p>
        <h1 className="text-3xl md:text-4xl font-bold">Notifications</h1>
      </div>
      <div className="card space-y-6">
        <div className="flex items-start gap-4">
          <Mail className="w-6 h-6 text-cyan-400 mt-1 shrink-0" />
          <div className="flex-1">
            <h3 className="font-semibold">Weekly safety email</h3>
            <p className="text-sm text-slate-400 mt-1">
              Every Monday at 9:00 UTC we email <span className="font-mono text-slate-200">{s.email}</span> a summary of your scans, the threats caught, and your 5 riskiest scans from the past 7 days.
            </p>
          </div>
          <Switch data-testid="weekly-email-switch" checked={s.weekly_email} onCheckedChange={toggle} />
        </div>
        <div className="border-t border-slate-800 pt-5 flex items-center justify-between gap-4">
          <p className="text-sm text-slate-400">Want to see what it looks like? Send this week's summary to yourself now.</p>
          <button data-testid="send-digest-now-btn" disabled={busy} onClick={sendNow} className="btn-ghost flex items-center gap-2 whitespace-nowrap">
            <Send className="w-4 h-4" /> {busy ? "Sending..." : "Send me a summary now"}
          </button>
        </div>
      </div>
    </div>
  );
}
