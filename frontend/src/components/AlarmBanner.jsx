import { useEffect, useRef } from "react";
import { Siren, X } from "lucide-react";

function useSiren(active) {
  const ctxRef = useRef(null);
  useEffect(() => {
    if (!active) return;
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctxRef.current = ctx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = 0.06;
    osc.type = "sawtooth";
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    let up = true;
    const id = setInterval(() => {
      osc.frequency.setTargetAtTime(up ? 960 : 620, ctx.currentTime, 0.12);
      up = !up;
    }, 450);
    return () => {
      clearInterval(id);
      osc.stop();
      ctx.close();
    };
  }, [active]);
}

export const AlarmBanner = ({ score, host, soundOn, onDismiss }) => {
  useSiren(soundOn);
  return (
    <>
      <div className="alarm-perimeter" />
      <div
        data-testid="alarm-alert-banner"
        className="alarm-flash border-2 border-red-500/80 text-red-100 rounded-xl p-4 flex items-center justify-between gap-4 fade-up"
      >
        <div className="flex items-center gap-3">
          <Siren className="w-7 h-7 text-red-400 shrink-0" />
          <div>
            <p className="font-display font-bold text-lg">FRAUD ALARM: {host || "this site"} is dangerous</p>
            <p className="text-sm text-red-200/80">
              Security score {score}/100. Do not enter passwords, OTPs or payment details.
            </p>
          </div>
        </div>
        <button data-testid="alarm-dismiss-btn" onClick={onDismiss} className="btn-ghost border-red-400/60 flex items-center gap-1">
          <X className="w-4 h-4" /> Dismiss
        </button>
      </div>
    </>
  );
};
