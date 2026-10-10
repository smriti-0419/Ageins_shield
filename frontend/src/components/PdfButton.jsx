import { useState } from "react";
import { FileDown } from "lucide-react";
import { toast } from "sonner";
import { api, formatError } from "@/lib/api";

export const PdfButton = ({ scanId, compact = false, testId = "download-pdf-btn" }) => {
  const [busy, setBusy] = useState(false);
  if (!scanId) return null;
  const download = async () => {
    setBusy(true);
    try {
      const { data } = await api.get(`/history/${scanId}/pdf`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ageinsshield-report-${scanId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF report downloaded");
    } catch (e) {
      toast.error(formatError(e));
    }
    setBusy(false);
  };
  return (
    <button data-testid={testId} onClick={download} disabled={busy} title="Download PDF report"
      className={compact ? "text-slate-500 hover:text-cyan-300 transition-colors" : "btn-ghost flex items-center gap-2"}>
      <FileDown className="w-4 h-4" />
      {!compact && (busy ? "Preparing..." : "Download PDF")}
    </button>
  );
};
