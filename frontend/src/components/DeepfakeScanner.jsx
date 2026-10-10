import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, HelpCircle, Loader2, UploadCloud } from "lucide-react";
import { api } from "@/lib/api";

const MAX_IMAGE_MB = 10;
const MAX_VIDEO_MB = 50;

// Score = likelihood the media is manipulated (high is BAD, the opposite of the site security meter)
const tone = (score) =>
  score >= 65
    ? { text: "text-red-400", bar: "bg-red-500", Icon: AlertTriangle }
    : score >= 35
    ? { text: "text-amber-400", bar: "bg-amber-500", Icon: HelpCircle }
    : { text: "text-emerald-400", bar: "bg-emerald-500", Icon: CheckCircle2 };

const dot = { bad: "bg-red-500", warn: "bg-amber-500", info: "bg-sky-500", good: "bg-emerald-500" };

export const DeepfakeScanner = () => {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  // Preview URL for the chosen file. The cleanup function releases the memory.
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  const pick = (f) => {
    setResult(null);
    setError("");
    if (!f) return;
    const isImage = f.type.startsWith("image/");
    const isVideo = f.type.startsWith("video/");
    if (!isImage && !isVideo) {
      setError("Choose a photo (JPG, PNG, WebP) or a video (MP4, MOV, WebM).");
      return;
    }
    const limit = isImage ? MAX_IMAGE_MB : MAX_VIDEO_MB;
    if (f.size > limit * 1024 * 1024) {
      setError(`That ${isImage ? "photo" : "video"} is over ${limit} MB.`);
      return;
    }
    setFile(f);
  };

  const scan = async () => {
    if (!file) return;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/scan/media", form, { timeout: 180000 });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Scan failed. Is the backend running?");
    }
    setBusy(false);
  };

  const t = result ? tone(result.score) : null;

  return (
    <section
      data-testid="deepfake-scanner"
      className="w-full max-w-3xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-50"
    >
      <h2 className="text-xl font-semibold">Deepfake scanner</h2>
      <p className="mt-1 text-sm text-slate-400">
        Upload a photo or video. You get a manipulation score from 0 to 100, where a higher score means more
        likely fake.
      </p>

      <label
        htmlFor="deepfake-file"
        className="mt-5 flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-slate-700 p-6 text-center hover:border-cyan-500"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pick(e.dataTransfer.files?.[0]);
        }}
      >
        <UploadCloud className="h-8 w-8 text-cyan-400" />
        <span className="text-sm">{file ? file.name : "Click to choose a file, or drop it here"}</span>
        <span className="text-xs text-slate-500">Photos up to {MAX_IMAGE_MB} MB, videos up to {MAX_VIDEO_MB} MB</span>
        <input
          id="deepfake-file"
          ref={inputRef}
          data-testid="deepfake-input"
          type="file"
          accept="image/*,video/*"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0])}
        />
      </label>

      {previewUrl && file && (
        <div className="mt-4 overflow-hidden rounded-xl bg-black">
          {file.type.startsWith("video/") ? (
            <video src={previewUrl} controls className="mx-auto max-h-72" />
          ) : (
            <img src={previewUrl} alt="Selected upload" className="mx-auto max-h-72 object-contain" />
          )}
        </div>
      )}

      <button
        type="button"
        data-testid="deepfake-scan-btn"
        onClick={scan}
        disabled={!file || busy}
        className="mt-5 inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-2.5 font-semibold text-slate-950 disabled:opacity-50"
      >
        {busy && <Loader2 className="h-4 w-4 animate-spin" />}
        {busy ? "Analyzing..." : "Scan for deepfake"}
      </button>
      {busy && (
        <p className="mt-2 text-xs text-slate-400">
          Videos can take 10 to 30 seconds. The very first scan also downloads the AI model, which can take a few minutes.
        </p>
      )}
      {error && (
        <p data-testid="deepfake-error" className="mt-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {result && (
        <div data-testid="deepfake-result" className="mt-6 border-t border-slate-800 pt-5">
          <div className="flex items-center justify-between">
            <div className={`flex items-center gap-2 text-xl font-semibold ${t.text}`}>
              <t.Icon className="h-6 w-6" />
              {result.verdict}
            </div>
            <div className="text-2xl font-bold">{result.score}/100</div>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-800">
            <div className={`h-full ${t.bar} transition-all duration-700`} style={{ width: `${result.score}%` }} />
          </div>
          <p className="mt-1 text-xs text-slate-500">Manipulation likelihood (higher = more likely fake)</p>

          <ul className="mt-4 space-y-2">
            {result.signals.map((s, i) => (
              <li key={i} className="flex gap-3 rounded-lg border border-slate-800 p-3 text-sm">
                <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${dot[s.severity] || dot.info}`} />
                <div>
                  <div className="font-medium">{s.title}</div>
                  <div className="text-slate-400">{s.detail}</div>
                </div>
              </li>
            ))}
          </ul>

          {result.frames?.length > 0 && (
            <div className="mt-4">
              <div className="mb-1 text-xs text-slate-400">Score by moment in the video (seconds)</div>
              <div className="flex h-24 items-end gap-1">
                {result.frames.map((f, i) => (
                  <div key={i} className="flex flex-1 flex-col items-center justify-end" title={`${f.t}s: ${f.score}/100`}>
                    <div className={`w-full rounded-t ${tone(f.score).bar}`} style={{ height: `${Math.max(4, f.score)}%` }} />
                    <span className="mt-1 text-[10px] text-slate-500">{f.t}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <p className="mt-4 text-xs text-slate-500">{result.note}</p>
        </div>
      )}
    </section>
  );
};

export default DeepfakeScanner;
