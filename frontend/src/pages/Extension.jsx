import { Download, Puzzle } from "lucide-react";
import { BACKEND_URL } from "@/lib/api";

const steps = [
  "Download the extension ZIP and unzip it to a folder.",
  "Open chrome://extensions in Chrome (or edge://extensions in Edge).",
  "Turn on Developer mode (top-right toggle).",
  "Click 'Load unpacked' and select the unzipped 'aegisshield-extension' folder.",
  "Pin the AgeinsShield shield icon. Every site you open now gets a 1-100 badge.",
];

const perks = [
  ["Live badge", "The toolbar icon shows each site's score, colour-coded green / amber / red."],
  ["Fraud alarm", "Below 50, a flashing red bar, red frame, short siren and desktop notification appear."],
  ["Popup report", "Click the icon to see the verdict, domain age and every red flag."],
  ["Settings", "Change the API server, alarm threshold, or turn the alarm off."],
];

export default function Extension() {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-cyan-400 font-mono text-xs tracking-[0.3em] uppercase mb-3">Browser Extension</p>
        <h1 className="text-3xl md:text-4xl font-bold">Fraud alarm on every site you open</h1>
        <p className="text-slate-400 mt-2">A Chrome / Edge extension that scans each page automatically.</p>
      </div>
      <div className="card flex flex-col md:flex-row md:items-center gap-6">
        <Puzzle className="w-12 h-12 text-cyan-400 shrink-0" />
        <div className="flex-1">
          <h3 className="font-semibold text-lg">AgeinsShield Fraud Alarm v1.0</h3>
          <p className="text-sm text-slate-400">Manifest V3 · works in Chrome, Edge, Brave · already set to use this server</p>
        </div>
        <a data-testid="download-extension-btn" href={`${BACKEND_URL}/api/extension.zip`} className="btn-primary flex items-center gap-2 justify-center">
          <Download className="w-4 h-4" /> Download extension
        </a>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="font-semibold mb-4">Install in 1 minute</h3>
          <ol className="space-y-3" data-testid="extension-install-steps">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="font-mono text-cyan-400 shrink-0">0{i + 1}</span> {s}
              </li>
            ))}
          </ol>
        </div>
        <div className="card">
          <h3 className="font-semibold mb-4">What it does</h3>
          <ul className="space-y-3">
            {perks.map(([t, d]) => (
              <li key={t} className="text-sm"><p className="font-semibold text-slate-100">{t}</p><p className="text-slate-400">{d}</p></li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
