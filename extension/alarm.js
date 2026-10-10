// Injected into fraud pages: full-width flashing alarm bar + short siren.
(function () {
  if (window.__aegisAlarm) return;
  window.__aegisAlarm = true;
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type !== "aegis-alarm" || document.getElementById("aegis-alarm-bar")) return;
    const r = msg.result;
    const style = document.createElement("style");
    style.textContent =
      "@keyframes aegisFlash{from{background:#7f1d1d}to{background:#dc2626}}" +
      "#aegis-alarm-bar{position:fixed;top:0;left:0;right:0;z-index:2147483647;color:#fff;font:14px system-ui,sans-serif;padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:16px;animation:aegisFlash .8s infinite alternate;border-bottom:3px solid #fca5a5;box-shadow:0 6px 30px rgba(239,68,68,.5)}" +
      "#aegis-alarm-bar button{background:transparent;border:1px solid #fff;color:#fff;border-radius:6px;padding:6px 12px;cursor:pointer;font-weight:600}" +
      "#aegis-alarm-frame{position:fixed;inset:0;border:5px solid #ef4444;pointer-events:none;z-index:2147483646;animation:aegisFlash .8s infinite alternate}";
    document.documentElement.appendChild(style);
    const frame = document.createElement("div");
    frame.id = "aegis-alarm-frame";
    const bar = document.createElement("div");
    bar.id = "aegis-alarm-bar";
    const flags = (r.flags || []).slice(0, 3).map((f) => f.title).join(" · ");
    bar.innerHTML = "<div><b>AgeinsShield FRAUD ALARM</b> - this site scored <b></b>/100. <span></span></div><div><button id='aegis-leave'>Leave site</button> <button id='aegis-ignore'>Ignore</button></div>";
    bar.querySelector("b:nth-of-type(2)").textContent = r.score;
    bar.querySelector("span").textContent = flags;
    document.documentElement.appendChild(frame);
    document.documentElement.appendChild(bar);
    bar.querySelector("#aegis-leave").onclick = () => history.length > 1 ? history.back() : (location.href = "about:blank");
    bar.querySelector("#aegis-ignore").onclick = () => { bar.remove(); frame.remove(); };
    try {
      const ctx = new AudioContext();
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      g.gain.value = 0.05;
      o.type = "sawtooth";
      o.connect(g).connect(ctx.destination);
      o.start();
      let up = true;
      const id = setInterval(() => { o.frequency.value = up ? 960 : 620; up = !up; }, 400);
      setTimeout(() => { clearInterval(id); o.stop(); ctx.close(); }, 3000);
    } catch (e) {}
  });
})();
