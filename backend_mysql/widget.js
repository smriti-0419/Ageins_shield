/* AgeinsShield embeddable security chatbot - paste <script src=".../api/widget.js" defer></script> into any site */
(function () {
  if (window.__aegisLoaded) return;
  window.__aegisLoaded = true;
  var API = "__API_BASE__/api";
  var css = "" +
    ".ag-btn{position:fixed;bottom:22px;right:22px;width:60px;height:60px;border-radius:50%;background:#06B6D4;border:none;cursor:pointer;z-index:2147483646;box-shadow:0 0 0 6px rgba(6,182,212,.18),0 10px 30px rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;transition:transform .2s}" +
    ".ag-btn:hover{transform:scale(1.07)}" +
    ".ag-panel{position:fixed;bottom:94px;right:22px;width:350px;max-width:calc(100vw - 30px);height:500px;max-height:calc(100vh - 120px);background:#0F172A;color:#F8FAFC;border:1px solid #1E293B;border-radius:16px;z-index:2147483647;display:none;flex-direction:column;overflow:hidden;font-family:system-ui,-apple-system,Segoe UI,sans-serif;box-shadow:0 20px 50px rgba(0,0,0,.6)}" +
    ".ag-panel.open{display:flex}" +
    ".ag-head{padding:14px 16px;background:#070A12;border-bottom:1px solid #1E293B;display:flex;justify-content:space-between;align-items:center}" +
    ".ag-head b{font-size:15px}.ag-head small{color:#94A3B8;font-size:11px;display:block}" +
    ".ag-meter{padding:10px 16px;border-bottom:1px solid #1E293B;font-size:12px;color:#94A3B8}" +
    ".ag-bar{height:8px;border-radius:6px;background:#1E293B;margin-top:6px;overflow:hidden}.ag-fill{height:100%;transition:width .8s}" +
    ".ag-msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px}" +
    ".ag-m{max-width:85%;padding:9px 12px;border-radius:12px;font-size:13px;line-height:1.45;white-space:pre-wrap}" +
    ".ag-bot{background:#1E293B;align-self:flex-start}.ag-me{background:#06B6D4;color:#04121a;align-self:flex-end}" +
    ".ag-form{display:flex;border-top:1px solid #1E293B}.ag-form input{flex:1;background:#070A12;border:none;color:#F8FAFC;padding:13px;font-size:13px;outline:none}" +
    ".ag-form button{background:#06B6D4;border:none;color:#04121a;font-weight:700;padding:0 16px;cursor:pointer}" +
    ".ag-alarm{position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#7f1d1d;color:#fff;padding:12px 18px;font-family:system-ui,sans-serif;font-size:14px;display:flex;justify-content:space-between;align-items:center;animation:agp 1s infinite alternate;border-bottom:2px solid #EF4444}" +
    "@keyframes agp{from{background:#7f1d1d}to{background:#b91c1c}}" +
    ".ag-alarm button{background:transparent;border:1px solid #fff;color:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var shield = '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#04121a" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>';
  var btn = document.createElement("button"); btn.className = "ag-btn"; btn.innerHTML = shield; btn.setAttribute("aria-label", "Open AgeinsShield assistant");
  var panel = document.createElement("div"); panel.className = "ag-panel";
  panel.innerHTML = '<div class="ag-head"><div><b>Aegis Assistant</b><small>Fraud & phishing helper</small></div><span style="cursor:pointer;font-size:20px" id="ag-x">&times;</span></div>' +
    '<div class="ag-meter">This site security meter: <b id="ag-score">checking...</b><div class="ag-bar"><div class="ag-fill" id="ag-fill" style="width:0"></div></div></div>' +
    '<div class="ag-msgs" id="ag-msgs"></div><form class="ag-form" id="ag-form"><input id="ag-in" placeholder="Paste a link or ask a question..." autocomplete="off"/><button type="submit">Send</button></form>';
  document.body.appendChild(btn); document.body.appendChild(panel);

  var msgs = panel.querySelector("#ag-msgs");
  function add(text, me) { var d = document.createElement("div"); d.className = "ag-m " + (me ? "ag-me" : "ag-bot"); d.textContent = text; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; }
  function post(path, body) { return fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(function (r) { return r.json(); }); }
  function color(s) { return s >= 80 ? "#10B981" : s >= 50 ? "#F59E0B" : "#EF4444"; }

  btn.onclick = function () { panel.classList.toggle("open"); };
  panel.querySelector("#ag-x").onclick = function () { panel.classList.remove("open"); };
  add("Hi! I'm Aegis. Paste any link and I'll rate it 1-100, or ask 'is this site safe?'");

  panel.querySelector("#ag-form").onsubmit = function (e) {
    e.preventDefault();
    var input = panel.querySelector("#ag-in"); var text = input.value.trim(); if (!text) return;
    add(text, true); input.value = "";
    post("/chat", { message: text, page_url: location.href }).then(function (r) { add(r.reply); }).catch(function () { add("Connection error. Please try again."); });
  };

  if (!/^https?:$/.test(location.protocol)) { panel.querySelector("#ag-score").textContent = "preview mode (no live URL)"; return; }
  post("/scan/url", { url: location.href }).then(function (r) {
    var el = panel.querySelector("#ag-score"); el.textContent = r.score + "/100 - " + r.verdict; el.style.color = color(r.score);
    var f = panel.querySelector("#ag-fill"); f.style.width = r.score + "%"; f.style.background = color(r.score);
    if (r.is_fraud) {
      var a = document.createElement("div"); a.className = "ag-alarm";
      a.innerHTML = "<span><b>AgeinsShield ALERT:</b> this website scored " + r.score + "/100 and may be fraudulent. Do not enter passwords or payment details.</span><button>Dismiss</button>";
      a.querySelector("button").onclick = function () { a.remove(); };
      document.body.appendChild(a);
    }
  }).catch(function () { panel.querySelector("#ag-score").textContent = "unavailable"; });
})();
