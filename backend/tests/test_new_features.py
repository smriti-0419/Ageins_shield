"""New feature tests: domain_age, scan_id, PDF reports, extension.zip"""
import io
import os
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phishing-guard-61.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@aegisshield.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# -------- Domain age --------
def test_domain_age_trusted_github_null():
    r = requests.post(f"{API}/scan/url", json={"url": "https://github.com"})
    assert r.status_code == 200
    d = r.json()
    assert d["trusted"] is True
    assert d["domain_age"] is None


def test_domain_age_unregistered_flagged():
    # extremely unlikely to be registered
    url = "http://this-domain-definitely-does-not-exist-aegis-test-xyz123abc.com/login"
    r = requests.post(f"{API}/scan/url", json={"url": url})
    assert r.status_code == 200
    d = r.json()
    assert d["domain_age"] is not None
    # Could be unregistered or unknown depending on RDAP coverage; accept either but validate structure
    assert "status" in d["domain_age"]
    assert "age_days" in d["domain_age"]
    assert "created" in d["domain_age"]
    if d["domain_age"]["status"] == "unregistered":
        assert any("not registered" in f["title"].lower() for f in d["flags"])


def test_domain_age_registered_known_old_domain():
    # Use a non-trusted-list but very old registered domain
    r = requests.post(f"{API}/scan/url", json={"url": "https://example.org"})
    assert r.status_code == 200
    d = r.json()
    assert d["domain_age"] is not None
    assert d["domain_age"]["status"] in ("registered", "unknown")


# -------- scan_id presence --------
def test_scan_id_null_when_anonymous():
    r = requests.post(f"{API}/scan/url", json={"url": "https://github.com"})
    assert r.status_code == 200
    assert r.json().get("scan_id") is None


def test_scan_id_present_when_logged_in_url(headers):
    r = requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json().get("scan_id"), str) and len(r.json()["scan_id"]) == 24


def test_scan_id_present_when_logged_in_ai(headers):
    text = ("Yesterday I grabbed coffee with Sam and we didn't stop laughing. He's got this weird "
            "habit of adding too much sugar lol. Anyway, I'm gonna call mom tonight.")
    r = requests.post(f"{API}/scan/ai", json={"text": text}, headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json().get("scan_id"), str)


def test_scan_id_none_for_insufficient_ai(headers):
    r = requests.post(f"{API}/scan/ai", json={"text": "too short"}, headers=headers)
    assert r.status_code == 200
    assert r.json().get("scan_id") is None


def test_scan_id_present_when_logged_in_email(headers):
    r = requests.post(f"{API}/scan/email", json={"content": "From: a@b.com\nhello world body here"}, headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json().get("scan_id"), str)


# -------- PDF endpoint --------
def test_pdf_requires_auth(headers):
    sc = requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=headers)
    sid = sc.json()["scan_id"]
    r = requests.get(f"{API}/history/{sid}/pdf")
    assert r.status_code == 401


def test_pdf_download_url(headers):
    sc = requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=headers)
    sid = sc.json()["scan_id"]
    r = requests.get(f"{API}/history/{sid}/pdf", headers=headers)
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_pdf_download_ai(headers):
    text = ("In today's fast-paced landscape it is important to note we must leverage robust solutions. "
            "Furthermore, this plays a crucial role in the ever-evolving realm. In conclusion delve deeper.")
    sc = requests.post(f"{API}/scan/ai", json={"text": text}, headers=headers)
    sid = sc.json()["scan_id"]
    r = requests.get(f"{API}/history/{sid}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_pdf_download_email(headers):
    sc = requests.post(f"{API}/scan/email", json={"content": "From: a@b.com\nhello body"}, headers=headers)
    sid = sc.json()["scan_id"]
    r = requests.get(f"{API}/history/{sid}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_pdf_other_user_404(headers):
    # register fresh user, request admin's scan
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    reg = requests.post(f"{API}/auth/register", json={"name": "T", "email": email, "password": "secret123"})
    other_tok = reg.json()["token"]
    sc = requests.post(f"{API}/scan/url", json={"url": "https://github.com"}, headers=headers)
    sid = sc.json()["scan_id"]
    r = requests.get(f"{API}/history/{sid}/pdf", headers={"Authorization": f"Bearer {other_tok}"})
    assert r.status_code == 404


# -------- Extension zip --------
def test_extension_zip():
    r = requests.get(f"{API}/extension.zip")
    assert r.status_code == 200
    assert "application/zip" in r.headers.get("content-type", "")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    required = ["aegisshield-extension/manifest.json", "aegisshield-extension/background.js",
                "aegisshield-extension/alarm.js", "aegisshield-extension/popup.html",
                "aegisshield-extension/popup.js"]
    for n in required:
        assert n in names, f"missing {n}"
    # icons
    assert any("icons/" in n and n.endswith(".png") for n in names)
    # MV3 manifest
    import json
    mf = json.loads(z.read("aegisshield-extension/manifest.json"))
    assert mf["manifest_version"] == 3
    # placeholder replaced in js
    bg = z.read("aegisshield-extension/background.js").decode()
    assert "__API_BASE__" not in bg
    assert "/api/scan/url" in bg


# -------- Chat still works with domain age --------
def test_chat_with_url_still_works():
    r = requests.post(f"{API}/chat", json={"message": "is https://github.com safe?"})
    assert r.status_code == 200
    d = r.json()
    assert "scan" in d
    assert d["scan"]["score"] >= 80
