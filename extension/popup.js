const $ = (id) => document.getElementById(id);
const color = (s) => (s >= 80 ? "#10B981" : s >= 50 ? "#F59E0B" : "#EF4444");

function render(r) {
  if (!r) {
    $("status").textContent = "This page can't be scanned (not a website or server unreachable).";
    $("result").style.display = "none";
    return;
  }
  $("status").textContent = "";
  $("result").style.display = "block";
  $("score").textContent = r.score;
  $("score").style.color = color(r.score);
  $("verdict").textContent = r.verdict;
  $("verdict").style.color = color(r.score);
  $("fill").style.width = r.score + "%";
  $("fill").style.background = color(r.score);
  $("host").textContent = r.host;
  const age = r.domain_age;
  $("age").textContent = age && age.created ? `Domain registered ${age.created} (${age.age_days} days ago)` : "";
  $("flags").innerHTML = "";
  (r.flags || []).forEach((f) => {
    const li = document.createElement("li");
    li.textContent = f.title;
    $("flags").appendChild(li);
  });
}

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const s = await chrome.storage.sync.get({ apiBase: "__API_BASE__", alarmOn: true, threshold: 50 });
  $("apiBase").value = s.apiBase;
  $("alarmOn").checked = s.alarmOn;
  $("threshold").value = s.threshold;
  const cached = (await chrome.storage.session.get("tab:" + tab.id))["tab:" + tab.id];
  if (cached) render(cached);
  else chrome.runtime.sendMessage({ type: "rescan", tabId: tab.id, url: tab.url }, render);

  $("rescan").onclick = () => {
    $("status").textContent = "Scanning...";
    chrome.runtime.sendMessage({ type: "rescan", tabId: tab.id, url: tab.url }, render);
  };
  const host = /^https?:/.test(tab.url || "") ? new URL(tab.url).hostname.replace(/^www\./, "") : "";
  const { trusted } = await chrome.storage.sync.get({ trusted: [] });
  const setTrustLabel = (on) => ($("trust").textContent = on ? "Untrust this site" : "Trust this site");
  setTrustLabel(trusted.includes(host));
  $("trust").style.display = host ? "inline-block" : "none";
  $("trust").onclick = async () => {
    const { trusted } = await chrome.storage.sync.get({ trusted: [] });
    const next = trusted.includes(host) ? trusted.filter((d) => d !== host) : [...trusted, host];
    await chrome.storage.sync.set({ trusted: next });
    setTrustLabel(next.includes(host));
    chrome.runtime.sendMessage({ type: "rescan", tabId: tab.id, url: tab.url }, render);
  };
  $("save").onclick = async () => {
    await chrome.storage.sync.set({
      apiBase: $("apiBase").value.trim().replace(/\/$/, ""),
      alarmOn: $("alarmOn").checked,
      threshold: parseInt($("threshold").value, 10) || 50,
    });
    $("save").textContent = "Saved";
  };
}

init();
