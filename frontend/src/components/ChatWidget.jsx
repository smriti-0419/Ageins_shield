import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send, ShieldCheck, X } from "lucide-react";
import { api } from "@/lib/api";

export const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState([
    { me: false, text: "Hi! I'm Aegis. Paste any link and I'll rate it 1-100, or ask me about phishing and scams." },
  ]);
  const endRef = useRef(null);
  useEffect(() => {
  endRef.current?.scrollIntoView({ behavior: "smooth" });
}, [msgs]);

  const send = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    setMsgs((m) => [...m, { me: true, text }]);
    setInput("");
    setBusy(true);
    try {
      const { data } = await api.post("/chat", { message: text, page_url: window.location.href });
      setMsgs((m) => [...m, { me: false, text: data.reply }]);
    } catch {
      setMsgs((m) => [...m, { me: false, text: "Connection error, please try again." }]);
    }
    setBusy(false);
  };

  return (
    <>
      {open && (
        <div data-testid="chatbot-panel" className="fixed bottom-24 right-6 z-50 w-[350px] max-w-[calc(100vw-2rem)] h-[480px] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden fade-up">
          <div className="px-4 py-3 bg-[#070A12] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <div>
                <p className="font-display font-semibold text-sm">Aegis Assistant</p>
                <p className="text-[11px] text-slate-400">Rule-based security helper</p>
              </div>
            </div>
            <button data-testid="chatbot-close-btn" onClick={() => setOpen(false)}><X className="w-4 h-4 text-slate-400 hover:text-white" /></button>
          </div>
          <div data-testid="chatbot-messages" className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-thin">
            {msgs.map((m, i) => (
              <div key={i} className={`max-w-[85%] px-3 py-2 rounded-xl text-sm leading-relaxed ${m.me ? "ml-auto bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-100"}`}>
                {m.text}
              </div>
            ))}
            {busy && <div className="text-xs text-slate-500">Aegis is typing...</div>}
            <div ref={endRef} />
          </div>
          <form onSubmit={send} className="flex border-t border-slate-800">
            <input data-testid="chatbot-input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Paste a link or ask..." className="flex-1 bg-[#070A12] px-3 py-3 text-sm outline-none" />
            <button data-testid="chatbot-send-btn" type="submit" className="px-4 bg-cyan-500 text-slate-950"><Send className="w-4 h-4" /></button>
          </form>
        </div>
      )}
      <button data-testid="chatbot-trigger-btn" onClick={() => setOpen((o) => !o)} className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-cyan-500 text-slate-950 flex items-center justify-center shadow-[0_0_30px_rgba(6,182,212,0.45)] hover:scale-105 transition-transform">
        {!open && <span className="absolute inset-0 rounded-full bg-cyan-400/50 ping" />}
        {open ? <X className="w-6 h-6 relative" /> : <MessageSquare className="w-6 h-6 relative" />}
      </button>
    </>
  );
};
