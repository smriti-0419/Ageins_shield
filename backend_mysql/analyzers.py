import re
import statistics
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

TRUSTED_DOMAINS = {
    "google.com", "youtube.com", "microsoft.com", "apple.com", "amazon.com", "paypal.com",
    "github.com", "wikipedia.org", "facebook.com", "instagram.com", "linkedin.com", "netflix.com",
    "twitter.com", "x.com", "openai.com", "stackoverflow.com", "bing.com", "yahoo.com",
    "outlook.com", "live.com", "office.com", "dropbox.com", "adobe.com", "emergentagent.com",
}
BRANDS = ["paypal", "apple", "amazon", "microsoft", "google", "netflix", "facebook", "instagram",
          "bank", "chase", "wellsfargo", "hsbc", "sbi", "hdfc", "icici", "binance", "coinbase", "metamask", "office365", "outlook"]
SUSPICIOUS_TLDS = {"xyz", "top", "tk", "ml", "ga", "cf", "gq", "ru", "zip", "mov", "click", "country",
                   "kim", "work", "loan", "date", "racing", "review", "buzz", "rest", "cam", "su"}
SHORTENERS = {"bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "rb.gy", "shorturl.at"}
URL_KEYWORDS = ["login", "verify", "secure", "account", "update", "confirm", "banking", "wallet", "signin",
                "password", "free", "gift", "bonus", "prize", "claim", "unlock", "suspend", "airdrop", "recover"]


def _clamp(v, lo=1, hi=100):
    return max(lo, min(hi, int(round(v))))


LOOKALIKE_BRANDS = {
    "paypal": "paypal.com", "amazon": "amazon.com", "google": "google.com", "microsoft": "microsoft.com",
    "apple": "apple.com", "netflix": "netflix.com", "facebook": "facebook.com", "instagram": "instagram.com",
    "linkedin": "linkedin.com", "github": "github.com", "twitter": "twitter.com", "yahoo": "yahoo.com",
    "outlook": "outlook.com", "office": "office.com", "dropbox": "dropbox.com", "adobe": "adobe.com",
    "whatsapp": "whatsapp.com", "youtube": "youtube.com", "binance": "binance.com", "coinbase": "coinbase.com",
    "metamask": "metamask.io", "wellsfargo": "wellsfargo.com", "chase": "chase.com", "flipkart": "flipkart.com",
    "icici": "icicibank.com", "hdfc": "hdfcbank.com", "walmart": "walmart.com", "ebay": "ebay.com",
}
HOMOGLYPHS = [("rn", "m"), ("vv", "w"), ("cl", "d"), ("0", "o"), ("1", "l"), ("3", "e"), ("4", "a"),
              ("5", "s"), ("7", "t"), ("8", "b"), ("9", "g"), ("$", "s"), ("@", "a"), ("!", "i"), ("|", "l")]


def _edit_distance(a, b):
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def _deglyph(token):
    for fake, real in HOMOGLYPHS:
        token = token.replace(fake, real)
    return token


def find_lookalike(host: str):
    if _root_domain(host) in TRUSTED_DOMAINS:
        return None
    labels = host.split(".")[:-1]
    tokens = {t for label in labels for t in [label, *label.split("-")] if len(t) >= 4}
    for token in tokens:
        normalized = _deglyph(token)
        for brand, official in LOOKALIKE_BRANDS.items():
            if token == brand:
                continue
            if normalized == brand:
                return {"token": token, "brand": brand, "official": official, "technique": "swapped look-alike characters"}
            dist = _edit_distance(token, brand)
            if (dist == 1 and len(brand) >= 5) or (dist == 2 and len(brand) >= 8):
                return {"token": token, "brand": brand, "official": official, "technique": "typo-squatting, misspelled brand"}
    return None


def _level(score):
    if score >= 80:
        return "safe"
    if score >= 50:
        return "moderate"
    return "danger"


SECOND_LEVELS = {"co", "com", "org", "net", "gov", "ac", "edu", "nic", "res", "gen", "firm", "ind"}


def _root_domain(host):
    parts = host.split(".")
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVELS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def analyze_url(raw_url: str) -> dict:
    url = raw_url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "http://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    root = _root_domain(host)
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    flags, score = [], 100

    def flag(title, detail, penalty, severity="medium"):
        nonlocal score
        score -= penalty
        flags.append({"title": title, "detail": detail, "severity": severity})

    if not host:
        flag("Invalid URL", "The address could not be parsed into a valid host.", 70, "high")
    if parsed.scheme != "https":
        flag("No HTTPS", "Connection is not encrypted (HTTP). Data can be intercepted.", 20, "high")
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        flag("Raw IP address", "Legitimate sites rarely use a bare IP address as their host.", 30, "high")
    if "@" in raw_url:
        flag("'@' symbol in URL", "Browsers ignore everything before '@', a classic redirect trick.", 25, "high")
    if host.startswith("xn--") or ".xn--" in host:
        flag("Punycode domain", "Domain may use look-alike Unicode characters (homograph attack).", 30, "high")
    if tld in SUSPICIOUS_TLDS:
        flag("Suspicious TLD", f"The '.{tld}' extension is heavily abused by scammers.", 20, "medium")
    if host.count(".") >= 4:
        flag("Too many subdomains", "Deep subdomain chains are used to hide the real domain.", 15, "medium")
    if host.count("-") >= 2:
        flag("Many hyphens in domain", "Hyphen-stuffed domains often imitate real brands.", 10, "low")
    if len(url) > 100:
        flag("Very long URL", "Excessively long URLs can conceal malicious parameters.", 10, "low")
    if re.search(r"\d{3,}", root):
        flag("Numbers in domain", "Digits in the main domain can indicate a throwaway site.", 8, "low")
    if root in SHORTENERS:
        flag("URL shortener", "Shortened links hide the true destination.", 15, "medium")
    found_kw = [k for k in URL_KEYWORDS if k in url.lower()]
    if found_kw:
        flag("Phishing keywords", f"Contains bait words: {', '.join(found_kw[:5])}.", min(8 * len(found_kw), 24), "medium")
    if root not in TRUSTED_DOMAINS:
        imitated = [b for b in BRANDS if b in host]
        if imitated:
            flag("Brand impersonation", f"Uses brand name '{imitated[0]}' but is not the official domain.", 30, "high")
        look = find_lookalike(host)
        if look:
            flag("Look-alike domain", f"'{look['token']}' imitates '{look['brand']}' ({look['technique']}). "
                 f"The real site is {look['official']}.", 40, "high")
    if parsed.port and parsed.port not in (80, 443):
        flag("Unusual port", f"Uses non-standard port {parsed.port}.", 10, "low")

    trusted = root in TRUSTED_DOMAINS
    if trusted and parsed.scheme == "https":
        score = max(score, 95)
    result = {"url": raw_url, "host": host, "root_domain": root, "trusted": trusted, "flags": flags, "domain_age": None}
    return _finalize(result, score)


def normalize_domain(value: str) -> str:
    v = value.strip().lower()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", v):
        v = "http://" + v
    host = (urlparse(v).hostname or "").removeprefix("www.")
    if not re.match(r"^([a-z0-9-]+\.)+[a-z]{2,}$", host):
        return ""
    return _root_domain(host)


def _finalize(result, score):
    score = _clamp(score)
    level = _level(score)
    verdict = {"safe": "Looks safe", "moderate": "Proceed with caution", "danger": "Likely fraudulent"}[level]
    result.update(score=score, level=level, verdict=verdict, is_fraud=level == "danger")
    return result


_AGE_CACHE = {}


async def lookup_domain_age(root: str) -> dict:
    if root in _AGE_CACHE:
        return _AGE_CACHE[root]
    info = {"status": "unknown", "created": None, "age_days": None}
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as c:
            r = await c.get(f"https://rdap.org/domain/{root}")
        if r.status_code == 404 and "No RDAP service" not in r.text:
            info["status"] = "unregistered"
        elif r.status_code == 200:
            info["status"] = "registered"
            for e in r.json().get("events", []):
                if e.get("eventAction") == "registration":
                    created = datetime.fromisoformat(e["eventDate"].replace("Z", "+00:00"))
                    info["created"] = created.date().isoformat()
                    info["age_days"] = (datetime.now(timezone.utc) - created).days
    except (httpx.HTTPError, ValueError, KeyError):
        return info
    _AGE_CACHE[root] = info
    return info


async def full_url_scan(raw_url: str) -> dict:
    r = analyze_url(raw_url)
    if not r["host"] or re.match(r"^\d{1,3}(\.\d{1,3}){3}$", r["host"]) or r["trusted"]:
        return r
    info = await lookup_domain_age(r["root_domain"])
    r["domain_age"] = info
    age, score = info["age_days"], r["score"]

    def flag(title, detail, penalty, severity):
        nonlocal score
        score -= penalty
        r["flags"].append({"title": title, "detail": detail, "severity": severity})

    if info["status"] == "unregistered":
        flag("Domain not registered", f"'{r['root_domain']}' has no registration record - it may be fake or already taken down.", 30, "high")
    elif age is not None:
        if age < 30:
            flag("Brand-new domain", f"Registered only {age} days ago ({info['created']}). Most scam sites are under a month old.", 35, "high")
        elif age < 180:
            flag("Young domain", f"Registered {age} days ago ({info['created']}).", 20, "medium")
        elif age < 365:
            flag("Domain under a year old", f"Registered {age} days ago ({info['created']}).", 10, "low")
        elif age >= 1825:
            score += 5
    return _finalize(r, score)


AI_PHRASES = ["delve", "in conclusion", "furthermore", "moreover", "it is important to note", "tapestry",
              "in today's", "fast-paced", "landscape", "leverage", "seamless", "robust", "plays a crucial role",
              "it's worth noting", "in summary", "additionally", "navigate the", "realm", "pivotal", "foster",
              "embark", "unlock the", "a testament to", "ever-evolving", "holistic", "overall,", "crucial",
              "comprehensive", "multifaceted", "paramount", "underscore", "notably", "harness"]
CONTRACTIONS = re.compile(r"\b\w+'(t|s|re|ve|ll|d|m)\b", re.I)


def _sentence_ai_score(sentence):
    s = sentence.lower()
    hits = sum(1 for p in AI_PHRASES if p in s)
    words = len(sentence.split())
    score = 30 + hits * 22
    if 15 <= words <= 30:
        score += 12
    if CONTRACTIONS.search(sentence):
        score -= 15
    if re.search(r"[!?]{1}|\b(lol|lmao|haha|tbh|idk|gonna|wanna)\b", s):
        score -= 15
    return _clamp(score, 0, 100)


def analyze_ai_text(text: str) -> dict:
    clean = text.strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    words = re.findall(r"[A-Za-z']+", clean)
    wc = len(words)
    if wc < 20:
        return {"ai_probability": 0, "level": "insufficient", "verdict": "Need at least 20 words",
                "metrics": {"words": wc, "sentences": len(sentences)}, "sentences": [], "signals": []}

    lengths = [len(s.split()) for s in sentences] or [wc]
    mean_len = statistics.mean(lengths)
    burstiness = (statistics.pstdev(lengths) / mean_len) if mean_len else 0
    ttr = len(set(w.lower() for w in words)) / wc
    phrase_hits = sum(clean.lower().count(p) for p in AI_PHRASES)
    phrase_density = phrase_hits / max(1, len(sentences))
    contraction_rate = len(CONTRACTIONS.findall(clean)) / wc
    avg_word_len = statistics.mean(len(w) for w in words)

    score, signals = 40.0, []
    if burstiness < 0.35:
        score += 18
        signals.append("Uniform sentence lengths (low burstiness)")
    elif burstiness > 0.6:
        score -= 15
        signals.append("Varied sentence rhythm, typical of human writing")
    score += min(phrase_density * 25, 30)
    if phrase_hits:
        signals.append(f"{phrase_hits} AI-typical phrases detected")
    if contraction_rate < 0.005:
        score += 10
        signals.append("Almost no contractions (formal machine tone)")
    else:
        score -= min(contraction_rate * 600, 20)
        signals.append("Natural use of contractions")
    if avg_word_len > 5.2:
        score += 8
        signals.append("Long, formal vocabulary")
    if 0.45 <= ttr <= 0.65:
        score += 5

    prob = _clamp(score, 1, 99)
    level = "ai" if prob >= 65 else "mixed" if prob >= 40 else "human"
    verdict = {"ai": "Likely AI-generated", "mixed": "Mixed / uncertain", "human": "Likely human-written"}[level]
    return {
        "ai_probability": prob, "level": level, "verdict": verdict, "signals": signals,
        "metrics": {"words": wc, "sentences": len(sentences), "burstiness": round(burstiness, 2),
                    "vocabulary_richness": round(ttr, 2), "perplexity_index": _clamp(100 - prob + ttr * 20, 1, 100)},
        "sentences": [{"text": s, "score": _sentence_ai_score(s)} for s in sentences[:60]],
    }


URGENCY = ["urgent", "immediately", "within 24 hours", "act now", "suspended", "locked", "final notice",
           "expire", "unauthorized", "verify your account", "last warning", "asap", "right away"]
CREDENTIALS = ["password", "login", "verify your", "confirm your", "ssn", "social security", "otp",
               "pin", "credit card", "bank details", "account number", "cvv", "update your payment"]
MONEY = ["wire transfer", "gift card", "bitcoin", "crypto", "lottery", "winner", "prize", "inheritance",
         "refund", "invoice attached", "payment failed", "western union", "$", "₹"]
GENERIC = ["dear customer", "dear user", "dear valued", "dear account holder", "dear sir/madam", "hello user"]


def analyze_email(content: str, sender: str = "") -> dict:
    text = content or ""
    low = text.lower()
    flags, risk = [], 0

    def flag(title, detail, weight, severity="medium"):
        nonlocal risk
        risk += weight
        flags.append({"title": title, "detail": detail, "severity": severity})

    m = re.search(r"^from:\s*(.+)$", text, re.I | re.M)
    sender = sender or (m.group(1) if m else "")
    sender_dom = ""
    em = re.search(r"@([\w.-]+)", sender)
    if em:
        sender_dom = em.group(1).lower()
        imitated = [b for b in BRANDS if b in sender_dom and _root_domain(sender_dom) not in TRUSTED_DOMAINS]
        if imitated:
            flag("Deceptive sender domain", f"Sender '{sender_dom}' impersonates '{imitated[0]}'.", 30, "high")
        look = find_lookalike(sender_dom)
        if look:
            flag("Look-alike sender domain", f"'{look['token']}' imitates '{look['brand']}' ({look['technique']}).", 35, "high")
        if sender_dom.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
            flag("Suspicious sender TLD", f"Sender domain uses a high-risk extension.", 15, "medium")
        rt = re.search(r"^reply-to:.*@([\w.-]+)", text, re.I | re.M)
        if rt and _root_domain(rt.group(1).lower()) != _root_domain(sender_dom):
            flag("Reply-To mismatch", "Replies go to a different domain than the sender.", 20, "high")
    if re.search(r"^from:", text, re.I | re.M) and not re.search(r"dkim-signature|spf=pass|received-spf:\s*pass", low):
        flag("Missing SPF/DKIM", "No authentication headers found in the email.", 10, "low")

    u = [w for w in URGENCY if w in low]
    if u:
        flag("High urgency language", f"Pressure tactics: {', '.join(u[:4])}.", min(10 * len(u), 30), "high")
    c = [w for w in CREDENTIALS if w in low]
    if c:
        flag("Requests sensitive info", f"Asks for: {', '.join(c[:4])}.", min(12 * len(c), 30), "high")
    mo = [w for w in MONEY if w in low]
    if mo:
        flag("Money / payment bait", f"Mentions: {', '.join(mo[:4])}.", min(8 * len(mo), 24), "medium")
    g = [w for w in GENERIC if w in low]
    if g:
        flag("Generic greeting", f"Impersonal greeting '{g[0]}' instead of your name.", 10, "low")
    if re.search(r"\.(exe|scr|js|vbs|bat|zip|rar|iso|html?)\b", low) and "attach" in low:
        flag("Dangerous attachment", "References an executable or archive attachment.", 20, "high")
    if text.count("!") >= 3 or len(re.findall(r"\b[A-Z]{5,}\b", text)) >= 3:
        flag("Shouting / excessive punctuation", "Many CAPS words or exclamation marks.", 8, "low")

    links = re.findall(r"https?://[^\s\"'<>)]+", text)
    bad_links = []
    for link in links[:10]:
        r = analyze_url(link)
        if r["level"] != "safe":
            bad_links.append({"url": link, "score": r["score"]})
    if bad_links:
        flag("Suspicious links", f"{len(bad_links)} risky link(s) found, e.g. {bad_links[0]['url'][:60]}.",
             min(15 * len(bad_links), 35), "high")

    risk = _clamp(risk, 0, 100)
    level = "danger" if risk >= 55 else "moderate" if risk >= 25 else "safe"
    verdict = {"danger": "Phishing detected", "moderate": "Suspicious email", "safe": "Looks legitimate"}[level]
    return {"risk_score": risk, "safety_score": _clamp(100 - risk), "level": level, "verdict": verdict,
            "is_phishing": level == "danger", "sender_domain": sender_dom, "links": links[:10],
            "suspicious_links": bad_links, "flags": flags}


URL_RE = re.compile(r"((?:https?://)?(?:[\w-]+\.)+[a-z]{2,}(?:/[^\s]*)?)", re.I)


async def chatbot_reply(message: str, page_url: str = "") -> dict:
    msg = message.strip()
    low = msg.lower()
    m = URL_RE.search(msg)
    if m and "@" not in m.group(1):
        r = await full_url_scan(m.group(1))
        tips = "; ".join(f["title"] for f in r["flags"][:4]) or "no red flags found"
        return {"reply": f"Security meter for {r['host']}: {r['score']}/100 — {r['verdict']}. Findings: {tips}.",
                "scan": r}
    if any(k in low for k in ["this site", "this page", "this website", "current site", "check here", "is it safe"]) and page_url:
        r = await full_url_scan(page_url)
        return {"reply": f"This page ({r['host']}) scores {r['score']}/100 — {r['verdict']}.", "scan": r}
    if re.search(r"\b(hi|hello|hey|namaste|hola)\b", low):
        return {"reply": "Hi! I'm Aegis, your security assistant. Paste any link and I'll rate it 1-100, or ask me about phishing, passwords, scams or AI content."}
    if any(k in low for k in ["phish", "email", "scam mail", "spam"]):
        return {"reply": "Phishing red flags: urgent threats, requests for passwords/OTP, mismatched sender domains, generic greetings and odd links. Use the Phishing Email Detector to paste a full email for a verdict."}
    if any(k in low for k in ["password", "2fa", "otp", "account hacked", "hacked"]):
        return {"reply": "Use a unique 12+ character password per site, store them in a password manager, enable 2FA, and never share OTPs — no real company will ask for them. If hacked: change passwords now and log out other sessions."}
    if any(k in low for k in ["ai", "chatgpt", "generated", "written by"]):
        return {"reply": "The AI Content Detector checks burstiness, vocabulary, AI-typical phrases and contractions to estimate how likely a text is machine-written. Paste at least 20 words."}
    if any(k in low for k in ["fraud", "fake", "safe", "secure", "legit", "trust"]):
        return {"reply": "Before trusting a site: check for HTTPS, the exact domain spelling, odd extensions like .xyz/.top, and pressure to pay or log in. Paste the URL here and I'll score it."}
    if any(k in low for k in ["embed", "widget", "script", "install"]):
        return {"reply": "Go to the Embed page in the console, copy the one-line <script> tag and paste it before </body> on any website. I'll appear there and auto-check that page."}
    if any(k in low for k in ["help", "what can you do", "features"]):
        return {"reply": "I can: 1) rate any URL 1-100, 2) check the page you're on (ask 'is this site safe?'), 3) explain phishing signs, 4) give password & scam safety tips."}
    if any(k in low for k in ["thank", "thanks", "bye"]):
        return {"reply": "You're welcome. Stay sharp out there!"}
    return {"reply": "I'm not sure about that. Try pasting a link (e.g. paypal-verify.xyz), or ask 'is this site safe?', 'how to spot phishing?' or 'password tips'."}
