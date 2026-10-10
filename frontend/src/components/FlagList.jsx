import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

const sev = {
  high: { c: "text-red-400 border-red-500/30 bg-red-500/5", I: AlertTriangle },
  medium: { c: "text-amber-400 border-amber-500/30 bg-amber-500/5", I: AlertTriangle },
  low: { c: "text-slate-300 border-slate-600/40 bg-slate-500/5", I: Info },
};

export const FlagList = ({ flags = [], testId = "flag-list" }) => {
  if (!flags.length)
    return (
      <div data-testid={`${testId}-empty`} className="flex items-center gap-2 text-emerald-400 text-sm">
        <CheckCircle2 className="w-4 h-4" /> No red flags detected
      </div>
    );
  return (
    <ul data-testid={testId} className="space-y-2">
      {flags.map((f, i) => {
        const { c, I } = sev[f.severity] || sev.low;
        return (
          <li key={i} data-testid={`${testId}-item-${i}`} className={`border rounded-lg p-3 flex gap-3 fade-up ${c}`} style={{ animationDelay: `${i * 60}ms` }}>
            <I className="w-4 h-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-sm">{f.title}</p>
              <p className="text-xs text-slate-400 mt-0.5">{f.detail}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
};
