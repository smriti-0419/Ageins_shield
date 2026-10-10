import { levelColor } from "@/lib/api";

export const Gauge = ({ value = 0, level, label = "Security score", size = 220, testId = "security-gauge-meter" }) => {
  const r = 85;
  const circ = Math.PI * r;
  const pct = Math.max(0, Math.min(100, value)) / 100;
  const color = levelColor(level);
  return (
    <div data-testid={testId} className="flex flex-col items-center" style={{ width: size }}>
      <svg viewBox="0 0 200 115" width={size}>
        <path d="M15 100 A85 85 0 0 1 185 100" fill="none" stroke="#1E293B" strokeWidth="16" strokeLinecap="round" />
        <path
          d="M15 100 A85 85 0 0 1 185 100"
          fill="none"
          stroke={color}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - pct)}
          style={{ transition: "stroke-dashoffset 0.9s ease, stroke 0.4s ease", filter: `drop-shadow(0 0 8px ${color}66)` }}
        />
        <text x="100" y="92" textAnchor="middle" fill="#F8FAFC" fontSize="40" fontWeight="700" fontFamily="Outfit">
          {value}
        </text>
      </svg>
      <span className="text-xs uppercase tracking-[0.2em] text-slate-400 -mt-1" data-testid={`${testId}-label`}>
        {label}
      </span>
    </div>
  );
};
