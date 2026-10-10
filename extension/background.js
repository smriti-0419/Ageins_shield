// AgeinsShield background worker: scans each page you open and raises the fraud alarm.
const DEFAULT_API = "__API_BASE__";
const CACHE_MS = 10 * 60 * 1000;

async function settings() {
  const s = await chrome.storage.sync.get({ apiBase: DEFAULT_API, alarmOn: true, threshold: 50, trusted: [] });
  return s;
}

async function scan(url, force = false) {
  const key = "scan:" + url;
  if (!force) {
    const cached = (await chrome.storage.session.get(key))[key];
    if (cached && Date.now() - cached.at < CACHE_MS) return cached.result;
  }
  const { apiBase } = await settings();
  const res = await fetch(apiBase + "/api/scan/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  const result = await res.json();
  await chrome.storage.session.set({ [key]: { at: Date.now(), result } });
  return result;
}

function badgeColor(score) {
  return score >= 80 ? "#10B981" : score >= 50 ? "#F59E0B" : "#EF4444";
}

async function handleTab(tabId, url, force = false) {
  if (!url || !/^https?:/.test(url)) {
    chrome.action.setBadgeText({ tabId, text: "" });
    return null;
  }
  try {
    const r = await scan(url, force);
    await chrome.storage.session.set({ ["tab:" + tabId]: r });
    chrome.action.setBadgeText({ tabId, text: String(r.score) });
    chrome.action.setBadgeBackgroundColor({ tabId, color: badgeColor(r.score) });
    const { alarmOn, threshold, trusted } = await settings();
    const host = new URL(url).hostname.replace(/^www\./, "");
    const isTrusted = trusted.some((d) => host === d || host.endsWith("." + d));
    if (isTrusted) {
      chrome.action.setBadgeText({ tabId, text: "OK" });
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#10B981" });
    }
    if (alarmOn && !isTrusted && r.score < threshold) {
      chrome.notifications.create("aegis-" + tabId, {
        type: "basic",
        iconUrl: "icons/icon128.png",
        title: "FRAUD ALARM: " + r.host,
        message: `Security score ${r.score}/100 - ${r.verdict}. Do not enter passwords or payment details.`,
        priority: 2,
      });
      chrome.scripting.executeScript({ target: { tabId }, files: ["alarm.js"] }).then(() =>
        chrome.tabs.sendMessage(tabId, { type: "aegis-alarm", result: r })
      ).catch(() => {});
    }
    return r;
  } catch (e) {
    chrome.action.setBadgeText({ tabId, text: "?" });
    chrome.action.setBadgeBackgroundColor({ tabId, color: "#64748B" });
    return null;
  }
}

chrome.tabs.onUpdated.addListener((tabId, info, tab) => {
  if (info.status === "complete") handleTab(tabId, tab.url);
});

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.type === "rescan") {
    handleTab(msg.tabId, msg.url, true).then(reply);
    return true;
  }
});
