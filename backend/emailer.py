import ipaddress
import logging
import os
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> str:
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": os.environ["EMAIL_FROM_NAME"]}
    if os.environ.get("EMAIL_REPLY_TO"):
        payload["contact_email"] = os.environ["EMAIL_REPLY_TO"]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                 headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


TYPE_LABEL = {"url": "Website", "ai": "AI text", "email": "Email"}
LEVEL_COLOR = {"safe": "#10B981", "human": "#10B981", "moderate": "#F59E0B", "mixed": "#F59E0B",
               "danger": "#EF4444", "ai": "#EF4444"}


def risk_of(scan: dict) -> int:
    return 100 - scan["score"] if scan["type"] == "url" else scan["score"]


def _defang(host: str) -> str:
    return host.replace(".", "[.]")


def _scan_label(scan: dict) -> str:
    if scan["type"] == "url":
        return _defang(scan["result"].get("host") or "unknown site")
    return f"{TYPE_LABEL[scan['type']]} scan"


def build_digest(name: str, scans: list, console_url: str):
    total = len(scans)
    threats = sum(1 for s in scans if s["level"] in ("danger", "ai"))
    counts = {t: sum(1 for s in scans if s["type"] == t) for t in TYPE_LABEL}
    riskiest = sorted(scans, key=risk_of, reverse=True)[:5]
    brand = escape(os.environ["EMAIL_FROM_NAME"])
    rows = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #e2e8f0">{TYPE_LABEL[s["type"]]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e2e8f0;font-family:monospace">{escape(_scan_label(s))}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e2e8f0">{s["score"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e2e8f0;color:{LEVEL_COLOR.get(s["level"], "#64748b")};font-weight:bold">'
        f'{escape(s["verdict"])}</td></tr>'
        for s in riskiest
    ) or '<tr><td colspan="4" style="padding:12px;color:#64748b">No scans this week.</td></tr>'
    stat = lambda label, value, color="#0f172a": (
        f'<td style="padding:12px;background:#f1f5f9;border-radius:8px;text-align:center">'
        f'<div style="font-size:24px;font-weight:bold;color:{color}">{value}</div>'
        f'<div style="font-size:12px;color:#64748b">{label}</div></td>')
    html = (
        '<table role="presentation" width="100%" style="background:#f8fafc;padding:24px 0"><tr><td align="center">'
        '<table role="presentation" width="600" style="background:#ffffff;border-radius:12px;font-family:Arial,sans-serif;color:#0f172a">'
        f'<tr><td style="padding:24px;background:#070a12;color:#ffffff;border-radius:12px 12px 0 0">'
        f'<div style="color:#06b6d4;font-size:12px;letter-spacing:2px">{brand}</div>'
        '<div style="font-size:22px;font-weight:bold;margin-top:6px">Your weekly safety summary</div></td></tr>'
        f'<tr><td style="padding:24px"><p>Hi {escape(name)}, here is what your console caught in the last 7 days.</p>'
        '<table role="presentation" width="100%" cellspacing="8"><tr>'
        f'{stat("Total scans", total)}{stat("Threats caught", threats, "#EF4444")}'
        f'{stat("Websites", counts["url"])}{stat("Emails", counts["email"])}{stat("AI texts", counts["ai"])}</tr></table>'
        '<h3 style="margin:24px 0 8px">Riskiest scans</h3>'
        '<table role="presentation" width="100%" style="border-collapse:collapse;font-size:13px">'
        '<tr style="text-align:left;color:#64748b"><th style="padding:8px">Type</th><th style="padding:8px">Item</th>'
        f'<th style="padding:8px">Score</th><th style="padding:8px">Verdict</th></tr>{rows}</table>'
        f'<p style="margin-top:24px"><a href="{escape(console_url)}" style="background:#06b6d4;color:#04121a;padding:12px 20px;'
        'border-radius:8px;text-decoration:none;font-weight:bold">Open scan history</a></p>'
        f'<p style="font-size:12px;color:#94a3b8;margin-top:24px">Sent by {brand} because you turned on weekly summaries. '
        'Website names are shown with [.] so they are not clickable. We never ask for your password or payment details by email. '
        'You can turn these emails off in Settings.</p></td></tr></table></td></tr></table>')
    subject = f"{os.environ['EMAIL_FROM_NAME']} weekly summary: {threats} threat(s) in {total} scan(s)"
    return subject, html
